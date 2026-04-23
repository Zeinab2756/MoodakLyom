from __future__ import annotations

import os
from pathlib import Path

from app.schemas.emotion_schemas import EmotionDistribution


class AcousticEmotionPredictor:
    def __init__(self):
        self.model_name = os.getenv(
            "ACOUSTIC_EMOTION_MODEL_NAME",
            "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
        )
        self.target_sample_rate = int(os.getenv("ACOUSTIC_EMOTION_SAMPLE_RATE", "16000"))
        self.feature_extractor = None
        self.model = None
        self._torch = None
        self._librosa = None
        self._np = None
        self._soundfile = None
        self._device = "cpu"
        self._load_attempted = False

    def _ensure_loaded(self) -> None:
        if self.model is not None:
            return
        if self._load_attempted:
            raise RuntimeError("Acoustic emotion model is unavailable")

        self._load_attempted = True
        try:
            import librosa
            import numpy as np
            import soundfile
            import torch
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        except ImportError as exc:
            raise RuntimeError("Acoustic emotion dependencies are not installed") from exc

        self._librosa = librosa
        self._np = np
        self._soundfile = soundfile
        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(self.model_name)
        self.model.to(self._device)
        self.model.eval()

    def _load_audio(self, audio_path: str | Path):
        self._ensure_loaded()

        waveform, sample_rate = self._soundfile.read(str(audio_path), always_2d=False)
        waveform = self._np.asarray(waveform, dtype=self._np.float32)

        if waveform.ndim > 1:
            axis = 1 if waveform.shape[0] >= waveform.shape[1] else 0
            waveform = waveform.mean(axis=axis)

        if sample_rate != self.target_sample_rate:
            waveform = self._librosa.resample(
                waveform,
                orig_sr=sample_rate,
                target_sr=self.target_sample_rate,
            )

        return waveform

    def predict(self, audio_path: str | Path) -> EmotionDistribution:
        self._ensure_loaded()
        waveform = self._load_audio(audio_path)

        inputs = self.feature_extractor(
            waveform,
            sampling_rate=self.target_sample_rate,
            return_tensors="pt",
            padding=True,
        )
        inputs = {
            name: value.to(self._device)
            for name, value in inputs.items()
        }

        with self._torch.no_grad():
            logits = self.model(**inputs).logits
            probabilities = self._torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        distribution = {
            str(self.model.config.id2label[index]).strip().lower(): float(probability)
            for index, probability in enumerate(probabilities.tolist())
        }
        label, confidence = max(distribution.items(), key=lambda item: item[1])

        return EmotionDistribution(
            label=label,
            confidence=confidence,
            distribution=distribution,
            source="acoustic",
        )


acoustic_emotion_predictor = AcousticEmotionPredictor()


def predict_acoustic_emotion(audio_path: str | Path) -> EmotionDistribution:
    return acoustic_emotion_predictor.predict(audio_path)
