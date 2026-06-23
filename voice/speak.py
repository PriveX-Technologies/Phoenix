"""
Phoenix speak module — Text-to-Speech output with emotion-aware modifiers

Features:
  • Browser-based TTS via Web Speech API (primary)
  • Emotion-aware rate/pitch modifiers (happy/sad/angry/etc.)
  • Voice selection and persistence
  • Fallback handling and error recovery
"""

import json
from typing import Dict, Optional, Tuple

# ── Emotion TTS modifiers ──────────────────────────────────────────────────────
# Map emotions to (rate_mod, pitch_mod) to make speech feel more expressive
EMOTION_MODIFIERS = {
    "happy":    (1.15, 1.25),    # Faster, higher pitch
    "sad":      (0.85, 0.80),    # Slower, lower pitch
    "angry":    (1.20, 1.35),    # Fast, sharp pitch
    "anxious":  (1.10, 1.15),    # Slightly faster & higher
    "confused": (0.95, 0.95),    # Slightly slower
    "neutral":  (1.00, 1.00),    # No change
}

# ── Voice config (persists in session) ──────────────────────────────────────────
VOICE_CONFIG_SCHEMA = {
    "enabled": True,
    "voice": None,              # Browser voice name (auto-selected if None)
    "volume": 0.9,              # 0-1
    "rate": 1.05,               # 0.5-2.0
    "pitch": 1.0,               # 0.5-2.0
    "emotion_modifiers": True,  # Apply emotion-aware modifiers
}


def get_voice_modifiers(
    emotion: str,
    base_rate: float = 1.05,
    base_pitch: float = 1.0,
    apply_modifiers: bool = True
) -> Tuple[float, float]:
    """
    Calculate effective rate and pitch based on emotion.
    
    Args:
        emotion: emotion string (happy, sad, etc.)
        base_rate: base speaking rate
        base_pitch: base pitch level
        apply_modifiers: whether to apply emotion modifiers
    
    Returns:
        (final_rate, final_pitch)
    """
    if not apply_modifiers or emotion not in EMOTION_MODIFIERS:
        return base_rate, base_pitch
    
    rate_mod, pitch_mod = EMOTION_MODIFIERS[emotion]
    return base_rate * rate_mod, base_pitch * pitch_mod


def format_tts_payload(
    text: str,
    emotion: str = "neutral",
    voice_config: Optional[Dict] = None
) -> Dict:
    """
    Format a TTS payload for the frontend to consume.
    
    Args:
        text: Text to speak
        emotion: Detected emotion
        voice_config: Voice configuration dict
    
    Returns:
        Dict with TTS parameters for frontend Web Speech API
    """
    if voice_config is None:
        voice_config = VOICE_CONFIG_SCHEMA.copy()
    
    if not voice_config.get("enabled"):
        return None
    
    # Calculate emotion-aware rate/pitch
    rate, pitch = get_voice_modifiers(
        emotion,
        base_rate=voice_config.get("rate", 1.05),
        base_pitch=voice_config.get("pitch", 1.0),
        apply_modifiers=voice_config.get("emotion_modifiers", True)
    )
    
    return {
        "text": text,
        "voice": voice_config.get("voice"),
        "volume": voice_config.get("volume", 0.9),
        "rate": rate,
        "pitch": pitch,
        "emotion": emotion,
    }


def sanitize_tts_text(text: str) -> str:
    """
    Clean up text for TTS (remove URLs, mentions, etc.).
    
    Args:
        text: Raw text from Phoenix
    
    Returns:
        TTS-friendly version
    """
    # Remove URLs
    import re
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    
    # Remove excessive punctuation
    text = re.sub(r'([.!?]){2,}', r'\1', text)
    
    return text.strip()


# ── Quick test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("I'm so happy!", "happy"),
        ("That really saddens me.", "sad"),
        ("You're driving me crazy!", "angry"),
        ("I'm not sure about that.", "confused"),
        ("Hello there.", "neutral"),
    ]
    
    print("TTS modifier test:\n")
    for text, emotion in test_cases:
        rate, pitch = get_voice_modifiers(emotion)
        payload = format_tts_payload(text, emotion)
        print(f"  [{emotion:8s}] rate={rate:.2f}  pitch={pitch:.2f}")
        print(f"              text={text!r}\n")