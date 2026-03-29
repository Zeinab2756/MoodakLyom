# app/routes/voice.py

import os
import wave
import shutil
import json
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydub import AudioSegment
from pydub.utils import which
from vosk import Model, KaldiRecognizer

from app.models.emotion_model import emotion_classifier  # Hugging Face BERT

# --------------------------------------------------
# Router
# --------------------------------------------------
router = APIRouter(prefix="/voice", tags=["voice"])

# --------------------------------------------------
# Vosk model path
# --------------------------------------------------
# Project structure assumed:
# Moodmate/
#   models/vosk-small/...
#   app/routes/voice.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VOSK_MODEL_PATH = PROJECT_ROOT / "models" / "vosk-small"

if not VOSK_MODEL_PATH.exists():
    raise RuntimeError(f"Vosk model not found at {VOSK_MODEL_PATH}")

model = Model(str(VOSK_MODEL_PATH))
print(f"[INFO] Using Vosk model at: {VOSK_MODEL_PATH}")

# --------------------------------------------------
# Cross-platform temp directory for audio files
# --------------------------------------------------
BASE_TEMP_DIR = Path(tempfile.gettempdir()) / "moodmate_voice"
BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
print(f"[INFO] Temporary audio directory: {BASE_TEMP_DIR}")

# --------------------------------------------------
# Configure FFmpeg for pydub (force known path on Windows)
# --------------------------------------------------
ffmpeg_path = None

if os.name == "nt":  # Windows
    # 🔴 USE YOUR EXACT PATH HERE
    candidate = Path(r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe")
    if candidate.exists():
        ffmpeg_path = str(candidate)

# If we didn't find the hard-coded path (or on Mac/Linux), fall back to PATH
if ffmpeg_path is None:
    ffmpeg_path = which("ffmpeg")

if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    print(f"[INFO] Using ffmpeg at: {ffmpeg_path}")
else:
    # Not fatal for .wav input; MP3/M4A will fail with a clear error
    print(
        "[WARN] FFmpeg not found. "
        "MP3/M4A decoding may fail; WAV input will still work."
    )



# --------------------------------------------------
# Endpoint
# --------------------------------------------------
@router.post("/transcribe")
async def transcribe_voice(audio_file: UploadFile = File(...)):
    """
    Receives an audio file, converts it to PCM WAV if needed, transcribes it,
    analyzes the emotion from the text, and returns both.
    """
    tmp_path: Path | None = None
    pcm_path: Path | None = None

    try:
        print("[DEBUG] /voice/transcribe called")

        # ----- 1. Save uploaded audio to temp file -----
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = audio_file.filename or "audio"
        safe_name = original_name.replace(" ", "_")

        tmp_path = BASE_TEMP_DIR / f"{timestamp}_{safe_name}"
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(audio_file.file, f)

        print(f"[DEBUG] Uploaded audio saved at: {tmp_path}")

        # Determine extension
        ext = tmp_path.suffix.lower()

        # ----- 2. Ensure we have a mono 16k PCM WAV file -----
        if ext == ".wav":
            # If it's already WAV, use it directly (no ffmpeg needed)
            pcm_path = tmp_path
            print("[DEBUG] Input is WAV, skipping pydub conversion")
        else:
            if not ffmpeg_path:
                raise RuntimeError(
                    "Non-WAV input requires FFmpeg, but FFmpeg is not configured."
                )

            pcm_path = tmp_path.with_suffix(".pcm.wav")

            print("[DEBUG] Starting AudioSegment.from_file() for non-WAV input")
            try:
                audio = AudioSegment.from_file(str(tmp_path))
            except Exception as e:
                raise RuntimeError(f"Audio decoding via ffmpeg failed: {e!r}")

            audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

            print("[DEBUG] Exporting PCM WAV via ffmpeg")
            try:
                audio.export(str(pcm_path), format="wav")
            except Exception as e:
                raise RuntimeError(f"Audio export via ffmpeg failed: {e!r}")

            print(f"[DEBUG] Converted PCM WAV saved at: {pcm_path}")

        # ----- 3. Transcribe with Vosk -----
        print("[DEBUG] Starting Vosk transcription")
        try:
            with wave.open(str(pcm_path), "rb") as wf:
                rec = KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)

                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    rec.AcceptWaveform(data)

                result_json = json.loads(rec.FinalResult())
        except Exception as e:
            raise RuntimeError(f"Vosk transcription failed: {e!r}")

        final_text = result_json.get("text", "").strip()
        print(f"[INFO] Transcribed text: {final_text}")

        # ----- 4. Emotion Analysis -----
        if final_text:
            try:
                emotion_result = emotion_classifier.predict_emotion(final_text)
            except Exception as e:
                # Don't fail the whole endpoint if emotion model is weird
                print(f"[WARN] Emotion model failed: {e!r}")
                emotion_result = {
                    "primary_emotion": "neutral",
                    "confidence": 0.0,
                    "alternative_emotions": {},
                    "error": str(e),
                }
        else:
            emotion_result = {
                "primary_emotion": "neutral",
                "confidence": 0.0,
                "alternative_emotions": {},
            }

        # ----- 5. Return transcription + emotion -----
        return {
            "success": True,
            "transcribed_text": final_text,
            "emotion": emotion_result,
            "pcm_path": str(pcm_path),
        }

    except Exception as e:
        print(f"[ERROR] Transcription failed: {e!r}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not transcribe audio: {e}",
        )

    finally:
        # Optional cleanup: remove temp files
        try:
            if tmp_path and tmp_path.exists() and tmp_path != pcm_path:
                tmp_path.unlink()
            # Keep pcm_path if you want to debug; otherwise delete it too:
            # if pcm_path and pcm_path.exists():
            #     pcm_path.unlink()
        except Exception:
            # Ignore cleanup errors
            pass
