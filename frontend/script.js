import { PhoenixAnimator } from "./animation.js";
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

    list.innerHTML = Object.entries(data.facts).map(([k, v]) =>
      `<div class="fact-item"><span class="fact-key">${k}</span><span class="fact-val">${v}</span></div>`
    ).join('');
  } catch (e) {
    console.error("Facts load error:", e);
  }
}

function appendMessage(role, text, meta = {}) {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;

  const metaDiv = document.createElement('div');
  metaDiv.className = 'msg-meta';

  if (role === 'bot') {
    const emojis = {sad:'🤗', angry:'😌', anxious:'😊', happy:'😄', confused:'🤔', neutral:'🤖'};
    const emo = meta.emotion || 'neutral';
    metaDiv.textContent = `${emojis[emo] || '🤖'} Phoenix`;
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
  badge.className = `emotion-badge emotion-${emotion}`;
  badge.textContent = emotion;
  document.getElementById('toneHint').textContent = toneHint ? `— ${toneHint}` : '';
}

async function sendMessage() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  const btn = document.getElementById('sendBtn');
  btn.disabled = true;

  appendMessage('user', text);
  showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text}),
    });

    const data = await res.json();
    removeTyping();

    if (data.error) {
      appendMessage('bot', "Error: " + data.error, {emotion: 'neutral'});
    } else {
      updateEmotion(data.emotion, data.tone_hint);
      appendMessage('bot', data.reply, {emotion: data.emotion});
    }
  } catch (err) {
    removeTyping();
    appendMessage('bot', 'Connection error', {emotion: 'neutral'});
  }

  btn.disabled = false;
  input.focus();
}

document.getElementById('input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

appendMessage('bot', "Hello! I'm Phoenix 🚀", {emotion: 'happy'});