/**
 * Phoenix Frontend Script
 * Handles chat UI, message flow, and voice I/O integration
 */

// Lazy-load voice module after DOM is ready
let voiceModule = null;

async function initVoiceModule() {
    try {
        const { initVoice, speakReply } = await import('./voice.js');
        voiceModule = { initVoice, speakReply };
        voiceModule.initVoice();
        console.log("✅ Voice module loaded");
    } catch (e) {
        console.warn("⚠️  Voice module load error:", e);
        voiceModule = null;
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// FACTS PANEL
// ══════════════════════════════════════════════════════════════════════════════

let factsOpen = false;

function toggleFacts() {
    factsOpen = !factsOpen;
    document.getElementById('factsPanel').classList.toggle('open', factsOpen);
    if (factsOpen) loadFacts();
}

async function loadFacts() {
    try {
        const res = await fetch('/facts');
        const data = await res.json();
        const list = document.getElementById('factsList');

        if (!data.facts || Object.keys(data.facts).length === 0) {
            list.innerHTML = '<p class="no-facts">Nothing yet — tell me about yourself!</p>';
            return;
        }

        list.innerHTML = Object.entries(data.facts)
            .map(([k, v]) => `<div class="fact-item"><span class="fact-key">${k}</span><span class="fact-val">${v}</span></div>`)
            .join('');
    } catch (e) {
        console.error("❌ Facts load error:", e);
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// MESSAGE HANDLING
// ══════════════════════════════════════════════════════════════════════════════

const emotionEmojis = {
    sad: '🤗',
    angry: '😌',
    anxious: '😊',
    happy: '😄',
    confused: '🤔',
    neutral: '🤖'
};

function appendMessage(role, text, meta = {}) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const metaDiv = document.createElement('div');
    metaDiv.className = 'msg-meta';

    if (role === 'bot') {
        const emo = meta.emotion || 'neutral';
        const emoji = emotionEmojis[emo] || '🤖';
        metaDiv.textContent = `${emoji} Phoenix`;
    } else {
        metaDiv.textContent = 'You';
    }

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = text;

    div.appendChild(metaDiv);
    div.appendChild(bubble);
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function showTyping() {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot';
    div.id = 'typing';
    div.innerHTML = '<div class="msg-meta">🤖 Phoenix</div><div class="typing"><span></span><span></span><span></span></div>';
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
    const t = document.getElementById('typing');
    if (t) t.remove();
}

function updateEmotion(emotion, toneHint) {
    const badge = document.getElementById('emotionBadge');
    if (badge) {
        badge.className = `emotion-badge emotion-${emotion}`;
        badge.textContent = emotion.toUpperCase();
    }
    
    const hint = document.getElementById('toneHint');
    if (hint) {
        hint.textContent = toneHint ? `— ${toneHint}` : '';
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// CHAT FLOW
// ══════════════════════════════════════════════════════════════════════════════

async function sendMessage() {
    const input = document.getElementById('input');
    const text = input.value.trim();
    
    if (!text) return;

    input.value = '';
    const btn = document.getElementById('sendBtn');
    if (btn) btn.disabled = true;

    // Show user message immediately
    appendMessage('user', text);
    showTyping();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        const data = await res.json();
        removeTyping();

        if (data.error) {
            appendMessage('bot', `Error: ${data.error}`, { emotion: 'neutral' });
        } else {
            const emotion = data.emotion || 'neutral';
            const reply = data.reply || '';
            
            // Update emotion display
            updateEmotion(emotion, data.tone_hint);
            
            // Add bot message to chat
            appendMessage('bot', reply, { emotion });
            
            // Trigger voice output if module is loaded
            if (voiceModule && voiceModule.speakReply) {
                voiceModule.speakReply(reply, emotion);
            }
            
            // Update stats
            updateStats(data);
        }
    } catch (err) {
        removeTyping();
        console.error("❌ Chat error:", err);
        appendMessage('bot', 'Connection error — try again?', { emotion: 'neutral' });
    }

    if (btn) btn.disabled = false;
    input.focus();
}

function updateStats(data) {
    if (data.learned) {
        const el = document.getElementById('s-learned');
        if (el) el.textContent = (parseInt(el.textContent || 0) + 1).toString();
    }
    
    if (data.emotion) {
        const el = document.getElementById('s-emotion');
        if (el) el.textContent = data.emotion.toUpperCase();
    }
    
    if (data.score !== undefined) {
        const el = document.getElementById('s-score');
        if (el) el.textContent = data.score.toFixed(2);
    }
    
    const turnsEl = document.getElementById('s-turns');
    if (turnsEl) {
        const current = parseInt(turnsEl.textContent || 0);
        turnsEl.textContent = (current + 1).toString();
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// INPUT HANDLING
// ══════════════════════════════════════════════════════════════════════════════

const input = document.getElementById('input');
if (input) {
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

const sendBtn = document.getElementById('sendBtn');
if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
}

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════════════

// Show greeting
appendMessage('bot', "Hello! I'm Phoenix 🚀", { emotion: 'happy' });

// Initialize voice when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoiceModule);
} else {
    initVoiceModule();
}

// ══════════════════════════════════════════════════════════════════════════════
// EXPORTS (for inline script access)
// ══════════════════════════════════════════════════════════════════════════════

window.sendMessage = sendMessage;
window.toggleFacts = toggleFacts;
window.initVoiceModule = initVoiceModule;