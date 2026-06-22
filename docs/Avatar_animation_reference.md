# Avatar Animation Reference Guide

Complete visual + technical reference for Phoenix's cyber samurai animations.

---

## 🎬 Animation States Overview

### State Hierarchy

```
ROOT
├── idle
│   ├── breathing
│   ├── weight_shift
│   └── fidget (random)
│
├── emotional
│   ├── happy
│   ├── sad
│   ├── angry
│   ├── anxious
│   └── confused
│
└── action
    ├── listening
    ├── thinking
    ├── executing
    ├── success
    └── error
```

---

## 🎯 IDLE State (Default)

**Triggers:** No active processing, waiting for input

### Visual Description

```
┌─────────────────────────────────────┐
│         CYBER SAMURAI IDLE          │
│                                     │
│            🧘‍♂️                    │
│       (chest rising/falling)        │
│            ⚔️                       │
│      (sword spinning slowly)        │
│         ✨ ✨ ✨                   │
│  (ambient purple glow particles)    │
│                                     │
│    Stance: centered, relaxed        │
│    Breathing: 1 cycle per 5s        │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Duration | Loop |
|:-----|:----------|:---------|:-----|
| **Chest** | Scale Y: 1.0 → 1.05 → 1.0 | 5s | ∞ |
| **Pelvis** | Position X: -0.05 → +0.05 → -0.05 | 8s | ∞ |
| **Sword** | Rotation Z: 0 → 2π | 6s | ∞ |
| **Head** | Occasional tilt ±0.3 rad | 0.3s | Random |
| **Aura** | Opacity pulse 0.3 → 0.6 → 0.3 | 4s | ∞ |
| **Particles** | Ambient float upward | — | ∞ |

### Code Structure

```javascript
function updateIdle(deltaTime) {
    const t = elapsed % 5;
    const breathe = Math.sin((t / 5) * Math.PI * 2) * 0.05;
    chest.scale.y = 1.0 + breathe;
    
    const sway = Math.sin((elapsed / 8) * Math.PI * 2) * 0.05;
    pelvis.position.x = sway;
    
    sword.rotation.z += deltaTime * 0.3;  // Continuous spin
    
    // Random fidgets
    if (Math.random() < 0.001) {
        triggerFidget();
    }
    
    // Ambient particles
    if (Math.random() < 0.1) {
        emitParticle({
            position: samurai.position.clone().add(new Vector3(0, 0.5, 0)),
            velocity: new Vector3(0, 0.1, 0),
            color: 0x7C3AED,
            size: 0.02,
            lifetime: 2000
        });
    }
}
```

---

## 😊 HAPPY State

**Emotion trigger:** Positive sentiment detected

### Visual Description

```
┌─────────────────────────────────────┐
│         HAPPY SAMURAI               │
│                                     │
│           ✨🎉✨                   │
│     (bouncing, gleaming)            │
│            ⚡                       │
│      (sword radiates gold)          │
│   ✨ ✨ ✨ ✨ ✨                   │
│  (gold sparkles burst around body)  │
│                                     │
│    Stance: expanded, open           │
│    Color: Golden (#FFD700)          │
│    Speed: 1.3x normal               │
└─────────────────────────────────────┘
```

### Color Shift

```javascript
// From neutral gray to golden glow
material.color.lerp(
    new Color(0xA0A0A0),
    new Color(0xFFD700),
    0.8
);
material.emissive.setHex(0xFFD700);
material.emissiveIntensity = 0.6;
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Scale** | 1.0 → 1.15 | Body expands |
| **Breathing** | 1.5x faster | Energetic inhales |
| **Bouncing** | Y: 0 → 0.1 → 0 | Slight hop cycle |
| **Sword** | Glowing, faster spin | 1.5x rotation speed |
| **Arms** | Raised slightly | Open, welcoming |
| **Particles** | Gold sparkles burst | 30 particles, 20 emitted/sec |
| **Aura** | Bright golden, pulsing | Radius grows/shrinks |

### Code

```javascript
function updateHappy(deltaTime, intensity = 1.0) {
    const speed = 1.3 * intensity;
    
    // Bounce
    const bounce = Math.sin((elapsed * speed) * Math.PI * 2) * 0.08;
    samurai.position.y = baseY + bounce;
    
    // Expand
    samurai.scale.lerp(
        new Vector3(1.1, 1.1, 1.1),
        deltaTime * 2
    );
    
    // Golden glow
    material.emissive.setHSL(0.15, 1.0, 0.5);
    
    // Faster sword
    sword.rotation.z += deltaTime * 0.8;
    
    // Gold sparkle particles
    for (let i = 0; i < 5; i++) {
        emitParticle({
            position: samurai.position.clone().add(
                new Vector3(
                    (Math.random() - 0.5) * 0.5,
                    (Math.random() - 0.5) * 0.5,
                    (Math.random() - 0.5) * 0.5
                )
            ),
            velocity: randomSphere(0.5),
            color: 0xFFD700,
            size: 0.03,
            lifetime: 1000
        });
    }
}
```

---

## 😢 SAD State

**Emotion trigger:** Negative or melancholic sentiment

### Visual Description

```
┌─────────────────────────────────────┐
│         SAD SAMURAI                 │
│                                     │
│            🧠💙                    │
│      (drooped, dim, slow)           │
│            ↓                        │
│      (sword lowered)                │
│       💙 💙 💙                     │
│  (soft blue drift particles)        │
│                                     │
│    Stance: compressed, heavy        │
│    Color: Blue (#4A90E2)            │
│    Speed: 0.6x normal               │
└─────────────────────────────────────┘
```

### Color Shift

```javascript
material.color.lerp(
    new Color(0xA0A0A0),
    new Color(0x4A90E2),
    0.7
);
material.emissive.setHex(0x2E5C8A);
material.emissiveIntensity = 0.2;  // Dim
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Scale** | 1.0 → 0.85 | Body compresses |
| **Breathing** | 0.8x slower, shallow | Quiet, subdued |
| **Posture** | Spine forward-curve | Hunched |
| **Sword** | Lowered, slow rotation | 0.15x rotation speed |
| **Head** | Slight droop | Looking down |
| **Particles** | Blue drift, sparse | 5 particles/sec, slow |
| **Aura** | Dim blue, fading | Opacity low |

### Code

```javascript
function updateSad(deltaTime, intensity = 1.0) {
    const speed = 0.6 * intensity;
    
    // Compress body
    samurai.scale.lerp(
        new Vector3(0.85, 0.85, 0.85),
        deltaTime * 1.5
    );
    
    // Hunch spine
    spine.rotation.x = 0.3;
    head.rotation.x = 0.2;
    
    // Dim blue
    material.emissive.setHSL(0.58, 0.7, 0.3);
    
    // Slow sword
    sword.rotation.z += deltaTime * 0.15;
    
    // Slow blue particles (drift down)
    if (Math.random() < 0.3) {
        emitParticle({
            position: samurai.position.clone().add(
                new Vector3((Math.random() - 0.5) * 0.3, 0.5, 0)
            ),
            velocity: new Vector3(0, -0.05, 0),
            color: 0x4A90E2,
            size: 0.02,
            lifetime: 3000  // Longer life
        });
    }
}
```

---

## 😠 ANGRY State

**Emotion trigger:** Aggressive or frustrated sentiment

### Visual Description

```
┌─────────────────────────────────────┐
│         ANGRY SAMURAI               │
│                                     │
│        👹🔥👹                    │
│     (aggressive, burning)           │
│      🗡️⚡🗡️                       │
│   (sword ready, energy crackling)   │
│    🔴 🔴 🔴 🔴 🔴               │
│  (red energy burst, intense)        │
│                                     │
│    Stance: forward, tense           │
│    Color: Crimson (#FF4444)         │
│    Speed: 1.8x normal               │
│    Eyes: Glowing red (#FF0000)      │
└─────────────────────────────────────┘
```

### Color Shift & Effects

```javascript
material.color.setHex(0xFF4444);
material.emissive.setHex(0xFF0000);
material.emissiveIntensity = 0.8;  // Intense

// Eye glow (if eye geometry exists)
eyes.material.emissive.setHex(0xFF0000);
eyes.material.emissiveIntensity = 1.0;

// Aura pulse red
aura.material.color.setHex(0xFF2222);
aura.material.opacity = 0.7;
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Posture** | Forward lean | Aggressive stance |
| **Breathing** | 1.8x fast, heavy | Rapid, angry |
| **Sword** | Raised, vibrating | Ready to strike |
| **Arms** | Tensed, clenched | Fists ready |
| **Jitter** | Body trembles | 0.3 rad shake |
| **Head** | Glare, eyes bright | Red eyes glowing |
| **Particles** | Red energy burst | 40 particles/sec, fast |
| **Aura** | Pulsing crimson | Rapid pulse 0.4s cycle |

### Code

```javascript
function updateAngry(deltaTime, intensity = 1.0) {
    const speed = 1.8 * intensity;
    
    // Forward lean
    spine.rotation.x = 0.4;
    
    // Tense breathing
    const breathe = Math.sin((elapsed * speed) * Math.PI * 2) * 0.1;
    chest.scale.y = 1.0 + breathe;
    
    // Sword raised and vibrating
    sword.position.y = 0.8;
    sword.rotation.x = -0.3;
    const jitter = Math.random() - 0.5;
    sword.position.x += jitter * 0.05;
    
    // Red glow
    material.emissive.setHSL(0.0, 1.0, 0.5);
    
    // Body jitter
    const shake = (Math.random() - 0.5) * 0.1;
    samurai.position.x += shake;
    samurai.position.y += shake * 0.5;
    
    // Red energy burst
    for (let i = 0; i < 3; i++) {
        emitParticle({
            position: randomPointOnSamurai(),
            velocity: randomSphere(1.5),
            color: 0xFF4444,
            size: 0.035,
            lifetime: 800
        });
    }
}
```

---

## 🎤 LISTENING State

**Triggers:** Voice input active or user input detected

### Visual Description

```
┌─────────────────────────────────────┐
│         LISTENING SAMURAI           │
│                                     │
│       👂 ✨ 👂                    │
│   (ears focused, head tilted)       │
│            🧎                       │
│      (ready stance, attentive)      │
│      🎙️ 🎙️ 🎙️                 │
│  (sound wave ripples around body)   │
│                                     │
│    Stance: forward, alert           │
│    Color: Cyan glow (#00FF88)       │
│    Movement: Head toward sound      │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Head** | Tilt toward mic | 0.3 rad rotation |
| **Aura** | Cyan glow, pulsing | Listens intently |
| **Ears** | Geometry pulse | Rippling effect |
| **Arms** | Ready stance | Slight forward lean |
| **Particles** | Sound waves (concentric) | Cyan ripples from center |
| **Breathing** | Quick, focused | Anticipation |

### Code

```javascript
function updateListening(deltaTime) {
    // Tilt head toward sound source
    head.rotation.z = 0.3;
    head.rotation.x = 0.1;
    
    // Ready stance
    spine.rotation.x = 0.15;
    
    // Cyan glow
    aura.material.color.setHex(0x00FF88);
    aura.opacity = 0.5 + Math.sin(elapsed * 3) * 0.2;
    
    // Sound wave ripples (concentric circles)
    const rippleRadius = (elapsed * 1.5) % 1.5;
    emitSoundWave({
        position: samurai.position,
        radius: rippleRadius,
        color: 0x00FF88,
        opacity: 1.0 - rippleRadius / 1.5
    });
    
    // Quick, focused breathing
    const breathe = Math.sin((elapsed * 2.5) * Math.PI * 2) * 0.06;
    chest.scale.y = 1.0 + breathe;
}
```

---

## 💭 THINKING State

**Triggers:** Processing message, reasoning, planning

### Visual Description

```
┌─────────────────────────────────────┐
│         THINKING SAMURAI            │
│                                     │
│            🤔 ⚡                   │
│       (pacing, contemplative)       │
│    ⚔️        →        ⚔️           │
│  (sword raised overhead)            │
│    ⭐ ⭐ ⭐ ⭐ ⭐               │
│ (thought particles stream upward)   │
│                                     │
│    Stance: pacing side-to-side      │
│    Color: Purple (#7C3AED)          │
│    Movement: Deliberate, slow       │
│    Particles: Idea flow upward      │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Pacing** | Position X: -0.3 → +0.3 → -0.3 | Side-to-side movement |
| **Sword** | Raised, rotating slowly | Contemplation pose |
| **Aura** | Purple, pulsing intensity | Thinking depth |
| **Particles** | Purple stream upward | Ideas flowing |
| **Head** | Slight downward angle | Concentration |
| **Breathing** | Measured, steady | Deep thought |

### Code

```javascript
function updateThinking(deltaTime) {
    // Pacing
    const pace = Math.sin((elapsed * 1.5) * Math.PI * 2) * 0.3;
    pelvis.position.x = pace;
    
    // Sword raised
    sword.position.y = 0.5;
    sword.rotation.x = -0.5;
    sword.rotation.z += deltaTime * 0.2;  // Slow rotation
    
    // Purple glow
    material.emissive.setHSL(0.75, 1.0, 0.4);
    
    // Aura intensity pulse
    aura.intensity = 0.5 + Math.sin(elapsed * 1.5) * 0.25;
    
    // Thought stream particles (upward from head)
    if (Math.random() < 0.3) {
        emitParticle({
            position: head.position.clone(),
            velocity: new Vector3(0, 0.3, 0),
            color: 0x7C3AED,
            size: 0.025,
            lifetime: 2000
        });
    }
    
    // Head angle
    head.rotation.x = -0.1;
}
```

---

## ⚡ EXECUTING State

**Triggers:** Plugin command running, system action in progress

### Visual Description

```
┌─────────────────────────────────────┐
│         EXECUTING SAMURAI           │
│                                     │
│          🚀⚡🚀                    │
│      (fast movement, decisive)      │
│            ⚡⚡⚡                   │
│      (energy coursing)              │
│     💥 💥 💥 💥 💥              │
│  (golden energy burst, intensity)   │
│                                     │
│    Stance: forward, locked          │
│    Color: Golden (#FFD700)          │
│    Speed: 2.0x normal               │
│    Intensity: Maximum               │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Movement** | Fast forward thrust | Z: 0 → 0.2 → 0 (rapid) |
| **Sword** | Energy burst from blade | Glowing bright |
| **Posture** | Forward lean, locked | Ready for action |
| **Particles** | Golden burst, explosion | 50 particles, fast spread |
| **Aura** | Bright golden, pulsing fast | High intensity |
| **Breathing** | Explosive exhale | 3.0x speed |

### Code

```javascript
function updateExecuting(deltaTime) {
    // Fast forward movement
    const thrust = Math.sin((elapsed * 4) * Math.PI * 2) * 0.2;
    samurai.position.z = thrust;
    
    // Locked forward lean
    spine.rotation.x = 0.3;
    
    // Golden glow
    material.emissive.setHex(0xFFD700);
    material.emissiveIntensity = 0.9;
    
    // Sword energy
    sword.material.emissive.setHex(0xFFD700);
    sword.material.emissiveIntensity = 1.0;
    
    // Rapid breathing
    const breathe = Math.sin((elapsed * 3) * Math.PI * 2) * 0.1;
    chest.scale.y = 1.0 + breathe;
    
    // Golden energy burst
    for (let i = 0; i < 5; i++) {
        emitParticle({
            position: sword.position.clone(),
            velocity: randomSphere(2.0),
            color: 0xFFD700,
            size: 0.04,
            lifetime: 600
        });
    }
}
```

---

## 🏆 SUCCESS State

**Triggers:** Task completed, command executed successfully

### Visual Description

```
┌─────────────────────────────────────┐
│         SUCCESS SAMURAI             │
│                                     │
│         🎉✨🎉                    │
│      (victory pose, triumphant)     │
│      ✊        ✊                  │
│   (arms raised in victory)          │
│    🎆 🎆 🎆 🎆 🎆               │
│  (particle explosion, celebration)  │
│                                     │
│    Stance: Victory pose             │
│    Color: Neon green (#00FF00)      │
│    Particles: Explosion all around  │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Arms** | Both raised | X: -π/2 |
| **Aura** | Large, bright green | Explosion effect |
| **Particles** | Explosion, all directions | 100 particles burst |
| **Glow** | Bright neon green | emissiveIntensity: 1.0 |
| **Scale** | Brief expansion | 1.0 → 1.2 → 1.0 (0.5s) |
| **Sound** | (SFX if audio enabled) | Success chime |

### Code

```javascript
function updateSuccess(deltaTime) {
    // Victory pose
    arm_right.rotation.x = -Math.PI / 2;
    arm_left.rotation.x = -Math.PI / 2;
    
    // Bright neon green
    material.emissive.setHSL(0.33, 1.0, 0.5);
    material.emissiveIntensity = 1.0;
    
    // Scale pulse
    const pulse = 1.0 + Math.sin(elapsed * 3) * 0.15;
    samurai.scale.setScalar(pulse);
    
    // Aura explosion
    aura.scale.setScalar(2.0);
    aura.material.opacity = 0.8;
    
    // Particle explosion
    const explosionCenter = samurai.position;
    for (let i = 0; i < 20; i++) {
        emitParticle({
            position: explosionCenter.clone(),
            velocity: randomSphere(2.5),
            color: 0x00FF00,
            size: 0.05,
            lifetime: 1000
        });
    }
    
    // Brief duration (fade after 2s)
    if (elapsed > 2.0) {
        setState('idle');
    }
}
```

---

## ❌ ERROR State

**Triggers:** Command failed, error detected

### Visual Description

```
┌─────────────────────────────────────┐
│         ERROR SAMURAI               │
│                                     │
│         ⚠️ ❌ ⚠️                  │
│    (defensive, warning state)       │
│           🛡️                       │
│      (defensive stance)             │
│     🔴 🔴 🔴 🔴 🔴              │
│ (red warning pulses, alert)         │
│                                     │
│    Stance: Defensive                │
│    Color: Red (#FF0000)             │
│    Particles: Warning burst         │
│    Aura: Red, flashing             │
└─────────────────────────────────────┘
```

### Animation Breakdown

| Part | Animation | Effect |
|:-----|:----------|:-------|
| **Posture** | Defensive stance | Arms crossed |
| **Sword** | Raised shield | Protective position |
| **Aura** | Red, flashing | Warning strobe |
| **Particles** | Red burst | Alert animation |
| **Glow** | Bright red | Attention-grabbing |
| **Breathing** | Quick, shallow | Alarm state |

### Code

```javascript
function updateError(deltaTime) {
    // Defensive stance
    spine.rotation.x = -0.2;
    arm_right.rotation.x = Math.PI / 3;
    arm_left.rotation.x = Math.PI / 3;
    
    // Red warning
    material.emissive.setHex(0xFF0000);
    material.emissiveIntensity = 0.7;
    
    // Flashing aura
    const flash = Math.sin(elapsed * 5) > 0 ? 0.9 : 0.3;
    aura.material.opacity = flash;
    aura.material.color.setHex(0xFF0000);
    
    // Red warning particles
    for (let i = 0; i < 3; i++) {
        emitParticle({
            position: samurai.position.clone().add(
                new Vector3(0, Math.random() * 0.5, 0)
            ),
            velocity: new Vector3(0, 0.5, 0),
            color: 0xFF0000,
            size: 0.03,
            lifetime: 800
        });
    }
}
```

---

## 🎚️ State Transition System

Smooth blending between states:

```javascript
class StateTransition {
    constructor(fromState, toState, duration = 0.5) {
        this.fromState = fromState;
        this.toState = toState;
        this.duration = duration;
        this.elapsed = 0;
    }

    update(deltaTime) {
        this.elapsed += deltaTime;
        const t = Math.min(this.elapsed / this.duration, 1.0);
        
        // Blend between two states
        const fromValue = getStateValue(this.fromState);
        const toValue = getStateValue(this.toState);
        
        return lerp(fromValue, toValue, easeInOutQuad(t));
    }

    isComplete() {
        return this.elapsed >= this.duration;
    }
}
```

---

## 📊 Animation Parameter Matrix

Quick reference for all animatable parameters:

| Parameter | Range | Unit | Typical Values |
|:----------|:------|:-----|:---|
| Scale | 0.5 - 2.0 | ratio | idle: 1.0, happy: 1.15, sad: 0.85 |
| Opacity | 0.0 - 1.0 | alpha | 0.3 - 0.8 |
| Rotation | -π - +π | radians | varies by part |
| Position | -1 - +1 | units | pacing: ±0.3 |
| Emission | 0.0 - 1.0 | intensity | idle: 0.2, angry: 0.8 |
| Particle count | 0 - 100 | count/sec | ambient: 2-5, burst: 30-50 |
| Speed | 0.5 - 2.0 | multiplier | sad: 0.6, angry: 1.8 |

---

## 🔧 Tuning Checklist

- [ ] Does breathing look natural? (5s cycle recommended)
- [ ] Do emotions feel recognizable? (Test on non-designers)
- [ ] Are particles too sparse or too dense? (Target: 30-50 max at once)
- [ ] Do transitions feel smooth or jerky? (0.3-0.5s transitions)
- [ ] Is the samurai ever completely still? (Add micro-fidgets)
- [ ] Do colors match the emotion palette?
- [ ] Is performance acceptable? (Target: 60 FPS)

---

## 🎨 Extending with Custom States

Template for adding new emotional or action states:

```javascript
function updateCustomState(deltaTime, intensity = 1.0) {
    // 1. Update position/rotation
    samurai.position.y += Math.sin(elapsed * freq) * amplitude;
    
    // 2. Update scale
    samurai.scale.lerp(targetScale, deltaTime * speed);
    
    // 3. Update material color/emissive
    material.emissive.setHSL(hue, saturation, lightness);
    
    // 4. Emit particles
    if (Math.random() < particleChance) {
        emitParticle({
            position: particlePos,
            velocity: particleVel,
            color: particleColor,
            lifetime: particleLife
        });
    }
    
    // 5. Optional: Sound effect
    if (shouldPlaySound) {
        playSound('custom_state_sfx');
    }
}
```

Add to state dispatcher:

```javascript
const states = {
    idle: updateIdle,
    happy: updateHappy,
    sad: updateSad,
    angry: updateAngry,
    anxious: updateAnxious,
    confused: updateConfused,
    listening: updateListening,
    thinking: updateThinking,
    executing: updateExecuting,
    success: updateSuccess,
    error: updateError,
    custom: updateCustomState,  // NEW
};
```

---

## 📈 Performance Optimization Tips

1. **Particle pooling:** Reuse particles instead of creating/destroying
2. **LOD animations:** Reduce detail for distant viewers
3. **Batching:** Combine particle meshes when possible
4. **Cull unnecessary states:** Don't animate unseen parts
5. **Profile in DevTools:** Identify bottlenecks
6. **Test on target hardware:** Mobile vs desktop needs differ

---

## 🚀 Next Steps

1. Implement idle + breathing (foundation)
2. Add emotional color shifts
3. Build action states (listening, thinking, executing)
4. Polish transitions
5. Add particle effects
6. Tune per feedback
7. Optimize performance