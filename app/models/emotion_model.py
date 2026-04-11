from __future__ import annotations

import os
from pathlib import Path


class EmotionClassifier:
    def __init__(self):
        self.model_name = os.getenv("EMOTION_MODEL_NAME", "bhadresh-savani/bert-base-uncased-emotion")
        self.local_model_dir = Path(__file__).with_name("bert_emotion_model")
        self.tokenizer = None
        self.model = None
        self.emotions: dict[int, str] = {}
        self._torch = None
        self._functional = None
        self._load_attempted = False

    def _ensure_loaded(self) -> bool:
        if self.model is not None:
            return True
        if self._load_attempted:
            return False

        self._load_attempted = True
        try:
            import torch
            import torch.nn.functional as functional
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            return False

        model_source = self.local_model_dir if self.local_model_dir.exists() else self.model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_source)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_source)
        self.model.eval()
        self.emotions = dict(self.model.config.id2label)
        self._torch = torch
        self._functional = functional
        return True

    def predict_emotion(self, text: str):
        if not text:
            return {"primary_emotion": None, "confidence": 0.0, "alternative_emotions": []}
        if not self._ensure_loaded():
            return {"primary_emotion": None, "confidence": 0.0, "alternative_emotions": []}

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with self._torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = self._functional.softmax(logits, dim=1).squeeze().cpu().numpy()

        top3_idx = probs.argsort()[-3:][::-1]
        top3_emotions = [self.emotions[i] for i in top3_idx]
        top3_probs = [float(probs[i]) for i in top3_idx]

        return {
            "primary_emotion": top3_emotions[0],
            "confidence": top3_probs[0],
            "alternative_emotions": [
                {"emotion": emo, "probability": prob}
                for emo, prob in zip(top3_emotions, top3_probs)
            ],
        }


emotion_classifier = EmotionClassifier()
