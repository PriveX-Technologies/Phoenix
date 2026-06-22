Voice Input & Output
=====================

This document explains the voice features in Phoenix and how to use them.

Browser Voice Input
-------------------
- The frontend uses the Web Speech API (`SpeechRecognition`) via `frontend/voice-helper.js`.
- In supported browsers (Chrome, Edge, some Chromium builds), open the Voice Control panel and click "Start Listening".
- If the browser does not support `SpeechRecognition`, the Listen button will be disabled and a status message will explain that voice input is unavailable.
- Recognised speech is sent to the server as a chat message with `allow_loosened: true` so the backend relaxes conversational heuristics for voice paths.

Voice Output (TTS)
------------------
- The frontend uses the Web Speech API `SpeechSynthesis` for TTS.
- Configure voice, `volume`, `rate`, and `pitch` in the Voice Control panel. Use the Test button to verify.
- Phoenix applies an emotion-aware modifier to rate/pitch so spoken replies match the displayed emotion.

Server-side `/voice` Endpoint
-----------------------------
- `POST /voice` accepts an audio file (WAV or WebM) and returns a JSON object with `transcript` and Phoenix's reply.
- Server transcription uses `faster-whisper` if installed. Install with:

```
pip install faster-whisper
```

- Control the Whisper model size with the `WHISPER_MODEL` environment variable (default `tiny`).

Security and Safety
-------------------
- Voice-transcribed messages are routed with `allow_loosened=true` to avoid conversational filter false-positives, but the server still enforces a conservative safety blocklist for harmful instructions.
- The `/nolimits` plugin relaxes non-safety filters for the session but does not disable the safety blocklist.
- `godmode` persists raw turns for debugging/archival use — avoid enabling it for untrusted environments.

Troubleshooting
---------------
- No recognition in browser: ensure microphone permissions are granted and that your browser supports `SpeechRecognition`.
- `/voice` returns `faster-whisper not installed`: run `pip install faster-whisper` and restart the server.
- TTS is silent: ensure `auto-speak` is enabled in the Voice panel and the chosen `voice` is available in your OS/browser.

Developer notes
---------------
- Frontend speech helper: `frontend/voice-helper.js`
- Frontend wiring: `frontend/index.html` (Voice Control panel, `sendVoiceMessage` helper)
- Server `/voice` route: `src/web_ui.py`
- Backend chat filter bypass: `src/inference.py` and `src/filters.py` (filtering respects `allow_loosened`)

Quick test (browser):
1. Start Phoenix: `python main.py`
2. Open `http://localhost:5000`
3. Expand Voice Control and click "Start Listening". Speak then observe Phoenix's reply and TTS.

Quick test (curl):
```
curl -X POST http://localhost:5000/voice -F "audio=@recording.wav"
```


Acknowledgements
----------------
Voice pipeline is optional and designed for local, offline use where possible. If you need server-side transcription for large-scale usage, consider deploying a dedicated Whisper instance or using a hosted ASR service.
