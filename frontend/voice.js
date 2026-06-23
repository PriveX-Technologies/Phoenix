/**
 * Phoenix Voice Control Module
 * 
 * Handles all voice I/O:
 *   • Voice input (Web Speech API + server transcription)
 *   • Voice output (Web Speech API TTS with emotion modifiers)
 *   • UI state management and feedback
 *   • Voice configuration persistence
 */

import { createSpeechRecognition } from "./voice-helper.js";

// ══════════════════════════════════════════════════════════════════════════════
// STATE & CONFIG
// ══════════════════════════════════════════════════════════════════════════════

const VoiceState = {
    isListening: false,
    isSpeaking: false,
    currentUtterance: null,
    recognition: null,
    config: {
        enabled: true,
        voice: null,
        volume: 0.9,
        rate: 1.05,
        pitch: 1.0,
        emotion_modifiers: true,
    }
};

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════════════

export function initVoice() {
    console.log("🎤 Initializing voice system...");
    
    // Load saved config
    loadVoiceConfig();
    
    // Setup speech recognition
    setupSpeechRecognition();
    
    // Setup UI event listeners
    setupVoiceUI();
    
    // Populate voice options
    populateVoiceSelect();
    
    // Handle page visibility for cleanup
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && VoiceState.isListening) {
            stopListening();
        }
    });
    
    console.log("✅ Voice system ready");
}


function loadVoiceConfig() {
    const saved = localStorage.getItem("phoenix_voice_config");
    if (saved) {
        try {
            VoiceState.config = { ...VoiceState.config, ...JSON.parse(saved) };
        } catch (e) {
            console.warn("⚠️  Failed to load voice config:", e);
        }
    }
}


function saveVoiceConfig() {
    localStorage.setItem("phoenix_voice_config", JSON.stringify(VoiceState.config));
}


// ══════════════════════════════════════════════════════════════════════════════
// SPEECH RECOGNITION (INPUT)
// ══════════════════════════════════════════════════════════════════════════════

function setupSpeechRecognition() {
    const recognition = createSpeechRecognition(
        onVoiceResult,
        onVoiceStateChange
    );
    
    if (!recognition) {
        console.warn("⚠️  Web Speech API not available in this browser");
        disableVoiceInput();
        return;
    }
    
    VoiceState.recognition = recognition;
}


function onVoiceResult(transcript) {
    console.log("🎤 Transcribed:", transcript);
    
    if (!transcript || transcript.trim().length === 0) {
        updateVoiceStatus("No speech detected. Try again?", "warning");
        return;
    }
    
    // Send as regular chat message with voice flag
    sendVoiceMessage(transcript);
}


function onVoiceStateChange(state) {
    const statusEl = document.getElementById("voice-status");
    const badge = document.getElementById("speaking-badge");
    const listenBtn = document.getElementById("voice-listen-btn");
    
    console.log("🎤 Voice state:", state);
    
    if (state === "listening") {
        VoiceState.isListening = true;
        updateVoiceStatus("Listening...", "info");
        if (badge) badge.classList.add("show");
        if (listenBtn) listenBtn.textContent = "Stop Listening";
    } else if (state === "hearing") {
        updateVoiceStatus("I hear you... processing", "info");
    } else if (state === "processing") {
        updateVoiceStatus("Processing speech...", "info");
    } else if (state === "idle") {
        VoiceState.isListening = false;
        updateVoiceStatus("Ready to listen", "idle");
        if (badge) badge.classList.remove("show");
        if (listenBtn) listenBtn.textContent = "Start Listening";
    } else if (state.startsWith("error:")) {
        const error = state.replace("error:", "");
        updateVoiceStatus(`Error: ${error}`, "error");
        console.error("🎤 Speech recognition error:", error);
    }
}


function updateVoiceStatus(msg, type = "idle") {
    const statusEl = document.getElementById("voice-status");
    if (!statusEl) return;
    
    statusEl.textContent = msg;
    statusEl.style.color = {
        "info": "var(--accent)",
        "warning": "var(--accent3)",
        "error": "#f87171",
        "idle": "var(--text-dim)"
    }[type] || "var(--text)";
}


export function startListening() {
    if (!VoiceState.recognition) {
        updateVoiceStatus("Voice input not available", "error");
        return;
    }
    
    if (VoiceState.isListening) {
        stopListening();
        return;
    }
    
    try {
        VoiceState.recognition.start();
    } catch (e) {
        console.error("🎤 Failed to start listening:", e);
        updateVoiceStatus("Couldn't start listening", "error");
    }
}


export function stopListening() {
    if (VoiceState.recognition && VoiceState.isListening) {
        VoiceState.recognition.stop();
        VoiceState.isListening = false;
    }
}


function disableVoiceInput() {
    const btn = document.getElementById("voice-listen-btn");
    const statusEl = document.getElementById("voice-status");
    
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Voice Input Not Supported";
    }
    
    if (statusEl) {
        statusEl.textContent = "Your browser doesn't support voice input.";
        statusEl.style.color = "var(--accent3)";
    }
}


async function sendVoiceMessage(transcript) {
    const input = document.getElementById("input");
    if (!input) return;
    
    input.value = transcript;
    input.focus();
    
    // Trigger send after a brief delay for UX
    setTimeout(() => {
        const sendBtn = document.getElementById("sendBtn");
        if (sendBtn) sendBtn.click();
    }, 100);
}


// ══════════════════════════════════════════════════════════════════════════════
// SPEECH SYNTHESIS (OUTPUT)
// ══════════════════════════════════════════════════════════════════════════════

export function speak(text, emotion = "neutral") {
    if (!VoiceState.config.enabled) {
        console.log("🔇 Voice output disabled");
        return;
    }
    
    // Sanitize text
    text = sanitizeTTSText(text);
    
    if (!text) return;
    
    const synth = window.speechSynthesis;
    if (!synth) {
        console.warn("⚠️  Web Speech Synthesis not available");
        return;
    }
    
    // Cancel any ongoing speech
    synth.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Get effective rate/pitch with emotion modifier
    const { rate, pitch } = applyEmotionModifier(
        emotion,
        VoiceState.config.rate,
        VoiceState.config.pitch
    );
    
    utterance.voice = getSelectedVoice();
    utterance.volume = VoiceState.config.volume;
    utterance.rate = rate;
    utterance.pitch = pitch;
    utterance.lang = "en-US";
    
    // Callbacks
    utterance.onstart = () => {
        VoiceState.isSpeaking = true;
        const badge = document.getElementById("speaking-badge");
        if (badge) badge.classList.add("show");
    };
    
    utterance.onend = () => {
        VoiceState.isSpeaking = false;
        const badge = document.getElementById("speaking-badge");
        if (badge) badge.classList.remove("show");
    };
    
    utterance.onerror = (evt) => {
        console.error("🎤 TTS error:", evt.error);
        VoiceState.isSpeaking = false;
    };
    
    VoiceState.currentUtterance = utterance;
    synth.speak(utterance);
    
    console.log(`🔊 Speaking (${emotion}): ${text.slice(0, 60)}...`);
}


function applyEmotionModifier(emotion, baseRate, basePitch) {
    const modifiers = {
        happy:    { rate: 1.15, pitch: 1.25 },
        sad:      { rate: 0.85, pitch: 0.80 },
        angry:    { rate: 1.20, pitch: 1.35 },
        anxious:  { rate: 1.10, pitch: 1.15 },
        confused: { rate: 0.95, pitch: 0.95 },
        neutral:  { rate: 1.00, pitch: 1.00 },
    };
    
    const mod = modifiers[emotion] || modifiers.neutral;
    
    return {
        rate: baseRate * mod.rate,
        pitch: basePitch * mod.pitch
    };
}


function sanitizeTTSText(text) {
    // Remove URLs
    text = text.replace(/https?:\/\/\S+/g, "");
    
    // Remove markdown code blocks
    text = text.replace(/```[\s\S]*?```/g, "");
    text = text.replace(/`[^`]+`/g, "");
    
    // Remove excessive punctuation
    text = text.replace(/([.!?]){2,}/g, "$1");
    
    // Limit length to avoid long TTS
    const max = 500;
    if (text.length > max) {
        text = text.slice(0, max) + "...";
    }
    
    return text.trim();
}


function getSelectedVoice() {
    const voiceName = VoiceState.config.voice;
    if (!voiceName) return null;
    
    const voices = window.speechSynthesis.getVoices();
    return voices.find(v => v.name === voiceName) || null;
}


// ══════════════════════════════════════════════════════════════════════════════
// VOICE SELECT DROPDOWN
// ══════════════════════════════════════════════════════════════════════════════

function populateVoiceSelect() {
    const select = document.getElementById("voice-select");
    if (!select) return;
    
    const synth = window.speechSynthesis;
    if (!synth) {
        select.innerHTML = '<option>Voice not available</option>';
        select.disabled = true;
        return;
    }
    
    // Voices might not be loaded immediately
    const loadVoices = () => {
        const voices = synth.getVoices();
        
        select.innerHTML = '<option value="">Auto (Default)</option>';
        
        voices.forEach(voice => {
            const option = document.createElement("option");
            option.value = voice.name;
            option.textContent = `${voice.name} (${voice.lang})`;
            select.appendChild(option);
        });
        
        // Restore saved voice
        if (VoiceState.config.voice) {
            select.value = VoiceState.config.voice;
        }
    };
    
    // Load on demand
    if (synth.getVoices().length === 0) {
        synth.onvoiceschanged = loadVoices;
    } else {
        loadVoices();
    }
    
    // Handle selection
    select.addEventListener("change", (e) => {
        VoiceState.config.voice = e.target.value;
        saveVoiceConfig();
        console.log("🎤 Voice selected:", e.target.value);
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// UI SETUP
// ══════════════════════════════════════════════════════════════════════════════

function setupVoiceUI() {
    // Voice panel toggle
    const voiceHeader = document.getElementById("voice-header");
    if (voiceHeader) {
        voiceHeader.addEventListener("click", toggleVoicePanel);
    }
    
    // Voice output toggle
    const autoSpeakToggle = document.getElementById("auto-speak-toggle");
    if (autoSpeakToggle) {
        autoSpeakToggle.checked = VoiceState.config.enabled;
        autoSpeakToggle.addEventListener("change", (e) => {
            VoiceState.config.enabled = e.target.checked;
            saveVoiceConfig();
            console.log("🔊 Voice output:", e.target.checked ? "enabled" : "disabled");
        });
    }
    
    // Volume slider
    const volSlider = document.getElementById("vol-slider");
    if (volSlider) {
        volSlider.value = VoiceState.config.volume;
        volSlider.addEventListener("input", (e) => {
            VoiceState.config.volume = parseFloat(e.target.value);
            document.getElementById("vol-val").textContent = e.target.value;
            saveVoiceConfig();
        });
    }
    
    // Rate slider
    const rateSlider = document.getElementById("rate-slider");
    if (rateSlider) {
        rateSlider.value = VoiceState.config.rate;
        rateSlider.addEventListener("input", (e) => {
            VoiceState.config.rate = parseFloat(e.target.value);
            document.getElementById("rate-val").textContent = e.target.value;
            saveVoiceConfig();
        });
    }
    
    // Pitch slider
    const pitchSlider = document.getElementById("pitch-slider");
    if (pitchSlider) {
        pitchSlider.value = VoiceState.config.pitch;
        pitchSlider.addEventListener("input", (e) => {
            VoiceState.config.pitch = parseFloat(e.target.value);
            document.getElementById("pitch-val").textContent = e.target.value;
            saveVoiceConfig();
        });
    }
    
    // Listen button
    const listenBtn = document.getElementById("voice-listen-btn");
    if (listenBtn) {
        listenBtn.addEventListener("click", startListening);
    }
    
    // Test button
    const testBtn = document.getElementById("speak-test-btn");
    if (testBtn) {
        testBtn.addEventListener("click", () => {
            speak("Phoenix voice system is working! This is a test message.", "happy");
        });
    }
}


export function toggleVoicePanel() {
    const body = document.getElementById("voice-body");
    const chevron = document.getElementById("voice-chevron");
    
    if (!body) return;
    
    body.classList.toggle("collapsed");
    
    if (chevron) {
        chevron.classList.toggle("open");
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// GLOBAL EXPORTS (for HTML onclick handlers)
// ══════════════════════════════════════════════════════════════════════════════
// These functions are called directly from HTML: onclick="functionName()"
// They MUST be available on the window object

if (typeof window !== 'undefined') {
    window.toggleVoicePanel = toggleVoicePanel;
    window.startListening = startListening;
    window.stopListening = stopListening;
    window.speak = speak;
}


// ══════════════════════════════════════════════════════════════════════════════
// INTEGRATION HOOKS (called from main chat handler)
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Call this after a bot reply to play TTS if enabled.
 * Typically called from script.js appendMessage or similar.
 */
export function speakReply(text, emotion = "neutral") {
    if (VoiceState.config.enabled) {
        speak(text, emotion);
    }
}


/**
 * Stop any ongoing speech.
 */
export function stopSpeaking() {
    const synth = window.speechSynthesis;
    if (synth) {
        synth.cancel();
        VoiceState.isSpeaking = false;
        const badge = document.getElementById("speaking-badge");
        if (badge) badge.classList.remove("show");
    }
}


/**
 * Get current voice state for debugging.
 */
export function getVoiceState() {
    return {
        ...VoiceState,
        currentUtterance: VoiceState.currentUtterance ? "[SpeechSynthesisUtterance]" : null
    };
}