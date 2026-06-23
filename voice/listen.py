"""
Phoenix listen module — Server-side voice input handling

Features:
  • Whisper transcription (via faster-whisper)
  • Model size control and caching
  • Error recovery and fallback transcripts
  • Confidence scoring and language detection
  • Session-specific audio caching
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict
import json

# ── Lazy Whisper import (fallback-friendly) ────────────────────────────────────
_whisper_model = None
_whisper_size = None

def _get_whisper_model(size: str = "tiny"):
    """Lazy-load Whisper model to avoid startup overhead."""
    global _whisper_model, _whisper_size
    
    if _whisper_model is not None and _whisper_size == size:
        return _whisper_model
    
    try:
        from faster_whisper import WhisperModel
        print(f"🎤 Loading Whisper model '{size}'...")
        _whisper_model = WhisperModel(
            size,
            device="cpu",
            compute_type="int8",  # Quantized for speed
            num_workers=1,
            cpu_threads=4
        )
        _whisper_size = size
        print(f"✅ Whisper '{size}' ready")
        return _whisper_model
    except ImportError:
        print("⚠️  faster-whisper not installed. Install with:")
        print("   pip install faster-whisper")
        return None
    except Exception as e:
        print(f"⚠️  Whisper load error: {e}")
        return None


def transcribe_audio(
    audio_path: str,
    language: str = "en",
    confidence_threshold: float = 0.5
) -> Tuple[Optional[str], Dict]:
    """
    Transcribe audio file to text using Whisper.
    
    Args:
        audio_path: Path to WAV/WebM/MP3 audio file
        language: Language code ('en', 'fr', etc.) or 'auto'
        confidence_threshold: Skip segments below this confidence (0-1)
    
    Returns:
        (transcript, metadata_dict)
        metadata includes: confidence, language_detected, duration, segments_count
    """
    if not os.path.exists(audio_path):
        return None, {"error": "Audio file not found"}
    
    whisper = _get_whisper_model(os.environ.get("WHISPER_MODEL", "tiny"))
    if whisper is None:
        return None, {
            "error": "Whisper not available",
            "fallback": "Try saying that again?",
            "fix": "pip install faster-whisper"
        }
    
    try:
        # Transcribe with language detection
        segments, info = whisper.transcribe(
            audio_path,
            language=None if language == "auto" else language,
            beam_size=5,
            best_of=5,
            patience=1.0,
            condition_on_previous_text=False,  # Avoid hallucinations
            verbose=False
        )
        
        # Collect segments with confidence filtering
        transcripts = []
        total_confidence = 0.0
        segment_count = 0
        
        for segment in segments:
            if segment.confidence >= confidence_threshold:
                transcripts.append(segment.text.strip())
                total_confidence += segment.confidence
                segment_count += 1
        
        # Combine segments
        transcript = " ".join(transcripts).strip()
        
        if not transcript:
            return None, {
                "error": "No speech detected",
                "fallback": "I didn't catch that. Say it again?",
                "confidence": 0.0
            }
        
        # Calculate average confidence
        avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0
        
        return transcript, {
            "success": True,
            "confidence": avg_confidence,
            "language": info.language if hasattr(info, 'language') else language,
            "segments": segment_count,
            "duration_ms": int(info.duration * 1000) if hasattr(info, 'duration') else 0,
        }
        
    except Exception as e:
        return None, {
            "error": f"Transcription failed: {str(e)}",
            "fallback": "Sorry, I couldn't process that. Try again?",
            "traceback": str(e)
        }


def get_whisper_available() -> bool:
    """Check if faster-whisper is installed and functional."""
    try:
        import faster_whisper  # noqa
        return True
    except ImportError:
        return False


def estimate_audio_duration(audio_path: str) -> Optional[float]:
    """Estimate audio duration in seconds without loading the full model."""
    try:
        import wave
        with wave.open(audio_path, 'rb') as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / rate
    except Exception:
        return None


# ── Fallback handling ──────────────────────────────────────────────────────────
FALLBACK_RESPONSES = [
    "I didn't catch that. Can you say it again?",
    "Sorry, could you repeat that?",
    "Hmm, let me hear that again.",
    "I'm not sure I got that. Try once more?",
    "My ears are a bit fuzzy. Say that again?",
]


def get_fallback_response(reason: str = "") -> str:
    """Get a fallback response when transcription fails."""
    import random
    
    fallback = random.choice(FALLBACK_RESPONSES)
    
    if reason == "no_speech":
        return "I didn't hear anything. Speak up!"
    elif reason == "confidence":
        return "That was pretty quiet. Can you speak louder?"
    elif reason == "duration":
        return "That was too short. Give me a bit more to work with?"
    
    return fallback


# ── Quick test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Voice input module loaded.\n")
    print(f"Whisper available: {get_whisper_available()}")
    print(f"Fallback responses: {len(FALLBACK_RESPONSES)}")