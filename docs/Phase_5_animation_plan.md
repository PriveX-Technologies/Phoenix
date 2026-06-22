# Phase 5: Avatar Animation System Enhancement

**Goal:** Make the cyber samurai a living, emotionally expressive entity.

---

## 📋 Overview

Current state: Static 3D model rendering with basic emotion labeling.

Target state: Avatar that **moves, breathes, reacts, and embodies** Phoenix's cognitive state in real-time.

---

## 🎯 Key Deliverables

### 1. **Animation State Machine** *(Core)*

Replace static rendering with a state-driven animation system.

**File: `frontend/avatar.js`** (new)

```javascript
class AvatarController {
    constructor(scene, model) {
        this.state = 'idle';
        this.emotion = 'neutral';
        this.intensity = 1.0;
        this.animations = new Map();
        this.mixers = [];
        this.loadAnimations();
    }

    setState(newState, emotion = null, duration = 0.5) {
        // Blend between animations smoothly
        // Update emotion if provided
        // Trigger particle effects as needed
    }

    // State transitions
    idle() { /* breathing, micro-movements */ }
    listening() { /* head focus, ear tilt, glow */ }
    thinking() { /* pacing, sword raised, particles */ }
    executing() { /* rapid movement, decisive pose */ }
    happy() { /* bouncing, gleaming, expanded */ }
    sad() { /* drooped, slow sway, dim */ }
    angry() { /* aggressive, glowing eyes, aura */ }
    confused() { /* head tilts, uncertain stance */ }
    anxious() { /* fidgeting, pacing */ }
    success() { /* victory pose, explosion */ }
    error() { /* defensive, red warning */ }
}
```

**Key methods:**
- `setState(state, emotion, duration)`
- `blend(fromAnim, toAnim, duration)`
- `playEmoteParticles(emotion)`
- `updateIntensity(value)`

---

### 2. **Breathing & Idle Loops** *(Visual Life)*

Samurai should never be still. Always breathing, always present.

**Implementation:**

```javascript
// Chest bone animation (continuous loop)
chest.scale.y = 1.0 + Math.sin(elapsed * 1.2) * 0.05;  // Breathing

// Sword idle spin
sword.rotation.z += deltaTime * 0.3;

// Ambient particles (faint glow around body)
emitParticles('ambient', 0.5);  // Low frequency

// Occasional head tilt (looks around)
if (Math.random() < 0.01) {
    head.rotation.z = (Math.random() - 0.5) * 0.3;
    setTimeout(() => { head.rotation.z = 0; }, 300);
}

// Subtle weight shift (foot to foot)
pelvis.position.x = Math.sin(elapsed * 0.4) * 0.05;
```

**Result:** Avatar feels alive even in silence.

---

### 3. **Emotion-Driven Visuals** *(Expression)*

Emotions aren't labels—they're visual transformations.

**File: `frontend/emotions.js`** (new)

```javascript
const emotionTraits = {
    happy: {
        colorShift: { r: 1.0, g: 0.8, b: 0.2 },        // Golden glow
        posture: { scaleY: 1.1 },                       // Expanded
        particles: { color: '#FFD700', count: 20 },     // Gold sparks
        animSpeed: 1.3,                                 // Faster
        breathing: 1.5,                                 // Deeper
    },
    sad: {
        colorShift: { r: 0.4, g: 0.5, b: 1.0 },        // Dim blue
        posture: { scaleY: 0.85 },                      // Drooped
        particles: { color: '#4A90E2', count: 5 },      // Soft blue
        animSpeed: 0.6,                                 // Slower
        breathing: 0.8,                                 // Shallow
    },
    angry: {
        colorShift: { r: 1.0, g: 0.2, b: 0.2 },        // Red/crimson
        posture: { scaleY: 1.0, aggressive: true },
        particles: { color: '#FF4444', count: 30 },     // Red burst
        animSpeed: 1.8,                                 // Much faster
        eyeGlow: '#FF0000',
        auraColor: '#FF2222',
    },
    anxious: {
        colorShift: { r: 1.0, g: 0.5, b: 0.0 },        // Orange flicker
        posture: { fidget: true },
        particles: { color: '#FF8800', count: 15 },
        animSpeed: 1.5,
        jitterAmount: 0.3,                              // Body jitter
    },
    confused: {
        colorShift: { r: 0.7, g: 0.7, b: 0.7 },        // Gray/uncertain
        posture: { tiltCycle: true },                   // Head tilts repeatedly
        particles: { color: '#999999', count: 10 },
        animSpeed: 0.8,
    },
};

function applyEmotionTraits(avatar, emotion) {
    const traits = emotionTraits[emotion];
    // Animate color shift
    animateLerp(avatar.material.color, traits.colorShift, 500);
    // Apply posture changes
    applyPostureShift(avatar, traits.posture);
    // Emit particles
    emitParticles(traits.particles);
    // Update animation speeds
    updateAnimationSpeeds(traits.animSpeed);
}
```

---

### 4. **State-Based Animations** *(Action Visualization)*

User input → Phoenix thinks → Samurai moves.

**LISTENING State:**
```javascript
listening() {
    // Head tilts toward sound source
    head.rotation.z = 0.3;
    
    // Ear-like geometry pulses
    emitParticles('sound_waves', { 
        radius: 0.5, 
        height: 2.0,
        color: '#00FF88',
        frequency: 'rapid'
    });
    
    // Subtle arm movement (ready to act)
    arm_right.rotation.z += 0.1;
    
    // Breathing quickens (anticipation)
    chest.scale.y = 1.0 + Math.sin(elapsed * 2.0) * 0.08;
}
```

**THINKING State:**
```javascript
thinking() {
    // Pacing side-to-side
    pelvis.position.x = Math.sin(elapsed * 1.5) * 0.3;
    
    // Sword raised (contemplation)
    sword.rotation.x = -0.5;
    sword.position.y = 0.5;
    
    // Particle stream from head (ideas flowing)
    emitParticles('thought_stream', {
        origin: head.position,
        flow: 'upward',
        color: '#7C3AED',
        count: 5,
        duration: elapsed * 2
    });
    
    // Intensity pulsing
    aura.intensity = 0.5 + Math.sin(elapsed * 2) * 0.3;
}
```

**EXECUTING State:**
```javascript
executing() {
    // Fast, decisive movement
    pelvis.position.z += Math.sin(elapsed * 4) * 0.2;
    
    // Sword energy burst
    sword.material.emissive.setHSL(0.6, 1.0, 0.6);
    emitParticles('energy_burst', {
        position: sword.position,
        direction: 'forward',
        color: '#FFD700',
        count: 50,
        speed: 2.0
    });
    
    // Body tense, locked
    spine.rotation.x = 0.2;  // Forward lean
}
```

**SUCCESS State:**
```javascript
success() {
    // Victory pose
    arm_right.rotation.x = -Math.PI / 2;  // Raised
    arm_left.rotation.x = -Math.PI / 2;
    
    // Triumphant particle explosion
    emitParticles('victory_explosion', {
        center: samurai.position,
        radius: 2.0,
        color: '#00FF00',
        count: 100,
        spread: 'all_directions'
    });
    
    // Glowing aura burst
    aura.scale.setScalar(1.5);
    animateLerp(aura.scale, { x: 1.0, y: 1.0, z: 1.0 }, 800);
    
    // Shine effect
    samurai.material.emissive.setHSL(0.15, 1.0, 0.5);
}
```

---

### 5. **Particle System** *(Visual Polish)*

Particles sold emotions—they're not optional.

**File: `frontend/particles.js`** (new)

```javascript
class ParticleEmitter {
    constructor(scene) {
        this.scene = scene;
        this.particles = [];
    }

    emit(config) {
        // config: {
        //   type: 'spark' | 'wave' | 'stream' | 'burst' | 'ambient'
        //   color: '#XXXXXX',
        //   count: number,
        //   position: Vector3,
        //   velocity: Vector3 or { spread, speed }
        //   lifetime: ms,
        //   size: float
        // }
        
        for (let i = 0; i < config.count; i++) {
            const particle = createParticle(config);
            this.particles.push(particle);
        }
    }

    update(deltaTime) {
        this.particles.forEach((p, i) => {
            p.lifetime -= deltaTime;
            if (p.lifetime <= 0) {
                this.scene.remove(p.mesh);
                this.particles.splice(i, 1);
            } else {
                p.update(deltaTime);
            }
        });
    }
}

// Usage examples:
emitter.emit({
    type: 'spark',
    color: '#FFD700',
    count: 20,
    position: sword.position,
    velocity: { spread: 0.5, speed: 1.0 },
    lifetime: 500
});

emitter.emit({
    type: 'wave',
    color: '#00FF88',
    count: 1,
    position: head.position,
    lifetime: 1000,
    radius: 0.8
});
```

---

### 6. **Avatar-Emotion Sync** *(Integration)*

Connect emotion detection to visual state.

**File: `src/inference.py`** (modify)

```python
def respond(message: str, session_id: str) -> dict:
    """
    Returns:
    {
        "reply": "...",
        "emotion": "happy" | "sad" | "angry" | etc,
        "intensity": 0.0-1.0,
        "action_state": "listening" | "thinking" | "executing" | etc,
        "particles": {
            "type": "...",
            "intensity": 0.0-1.0
        }
    }
    """
    emotion = detect_emotion(message)
    intensity = calculate_intensity(message, emotion)
    
    # Determine action state based on task
    action_state = 'thinking'
    if is_executing_plugin(message):
        action_state = 'executing'
    
    # Generate response
    reply = llm_respond(message, emotion, session_id)
    
    # Post-process (persona, filler, etc)
    reply = apply_persona(reply, emotion)
    
    return {
        "reply": reply,
        "emotion": emotion.name,
        "intensity": intensity,
        "action_state": action_state,
        "particles": {
            "type": emotion_to_particles(emotion),
            "intensity": intensity
        }
    }
```

**File: `frontend/script.js`** (modify)

```javascript
async function sendMessage(text) {
    const response = await fetch('/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text })
    });
    
    const data = await response.json();
    
    // Update avatar based on response
    avatar.setState(
        data.action_state,      // 'thinking', 'executing', etc
        data.emotion,           // 'happy', 'sad', etc
        0.5                     // transition duration
    );
    
    avatar.updateIntensity(data.intensity);
    
    // Emit particles
    if (data.particles) {
        particleEmitter.emit({
            type: data.particles.type,
            intensity: data.particles.intensity
        });
    }
    
    // Display reply
    displayMessage('phoenix', data.reply);
}
```

---

### 7. **Voice-to-Animation Pipeline** *(Phase Integration)*

When Phoenix listens, it **shows** listening.

**File: `src/web_ui.py`** (modify)

```python
@app.route('/voice', methods=['POST'])
def voice_input():
    audio_file = request.files['audio']
    
    # Transcribe
    transcript = transcribe(audio_file)
    
    # Generate response (returns emotion, state, etc)
    response = chat_step(transcript, session_id)
    
    return jsonify({
        'transcript': transcript,
        'reply': response['reply'],
        'emotion': response['emotion'],
        'action_state': response['action_state'],
        'particles': response['particles']
    })
```

Frontend receives animation data immediately → avatar reacts while response plays.

---

### 8. **Animation Configuration** *(Tweaking)*

Make animations easily tunable via env vars.

**File: `.env`** (add)

```
# Avatar animation settings
ANIMATION_SPEED=1.0           # 0.5x to 2.0x global speed
EMOTION_INTENSITY=1.0         # 0.5x to 2.0x expression strength
PARTICLE_COUNT=1.0            # 0.2x to 3.0x particle density
BREATHING_RATE=1.0            # 0.5x to 2.0x breathing speed
IDLE_FIDGET_CHANCE=0.05       # Probability of random movement
```

**File: `frontend/config.js`**

```javascript
const config = {
    animation: {
        speed: parseFloat(process.env.ANIMATION_SPEED || 1.0),
        emotionIntensity: parseFloat(process.env.EMOTION_INTENSITY || 1.0),
        particleCount: parseFloat(process.env.PARTICLE_COUNT || 1.0),
        breathingRate: parseFloat(process.env.BREATHING_RATE || 1.0),
        idleFidgetChance: parseFloat(process.env.IDLE_FIDGET_CHANCE || 0.05),
    }
};
```

---

## 🛠️ Implementation Order

### Week 1: Foundation
- [ ] `frontend/avatar.js` — State machine
- [ ] `frontend/particles.js` — Particle system
- [ ] `frontend/emotions.js` — Emotion traits

### Week 2: State Animations
- [ ] Idle + breathing
- [ ] Listening
- [ ] Thinking
- [ ] Executing

### Week 3: Integration
- [ ] Modify `inference.py` to return animation metadata
- [ ] Modify `web_ui.py` voice route
- [ ] Connect frontend to backend animation data

### Week 4: Polish
- [ ] Tuning + tweaking
- [ ] Env var configuration
- [ ] Success/error states
- [ ] Particle fine-tuning

---

## 📊 Testing Checklist

- [ ] Avatar breathes continuously in idle
- [ ] Emotions change samurai appearance
- [ ] Listening state plays on voice input
- [ ] Thinking state shows during processing
- [ ] Executing state triggers on plugin commands
- [ ] Success state plays on task completion
- [ ] Particles emit correctly per emotion
- [ ] Smooth transitions between states
- [ ] Animation speeds adjustable via env vars
- [ ] No performance degradation

---

## 🎨 Visual Reference

### Color Palette (cyberpunk)

```
Neutral:  #A0A0A0 (gray)
Happy:    #FFD700 (gold)
Sad:      #4A90E2 (blue)
Angry:    #FF4444 (crimson)
Anxious:  #FF8800 (orange)
Confused: #999999 (dim gray)
Success:  #00FF00 (neon green)
Error:    #FF0000 (red)
Ambient:  #7C3AED (purple glow)
```

### Particle Dynamics

```
Ambient:       Slow, faint, always present
Sound waves:   Concentric circles, ripple effect
Thought:       Upward stream, purple
Energy:        Explosive burst, golden
Success:       All-directional explosion, green
Error:         Warning flash, red
```

---

## 🚀 Performance Notes

- Use GPU-accelerated particle systems (Three.js)
- Limit active particles to ~500 max
- Use LOD (level of detail) for distant animations
- Cache animation clips to avoid repeated compilation
- Profile on target hardware (measure FPS)

---

## 🔗 Related Issues / Notes

- Fine-tune personality para-processor to match animation state
- Add CLI flag `--no-animations` for headless testing
- Document custom animation creation in `plugins/README.md`