# Aether particle system tuning reference

This file is loaded on demand by the `particle-aesthetics` skill during critique workflows. It contains the working ranges for every tunable parameter in the particle system, the failure modes that map to each one, and the diagnostic questions to ask when reviewing code.

When critiquing, walk these sections in the order presented — they're sorted by aesthetic impact, highest first.

## How to use this reference

For each parameter:

1. **Find the current value** in the code (the relevant file is noted in each section)
2. **Compare against the working range** — if outside, it's a finding
3. **Identify the failure mode** that matches the deviation direction
4. **Assign severity** using the severity column
5. **Recommend a specific replacement value** from inside the working range

The "centered" column gives the value to recommend if you want to be safe. The "edge" columns are the boundaries — values outside these produce visible failure modes.

---

## 1. BLOOM (highest aesthetic impact)

**File:** `frontend/src/particle/renderer.ts`

**Why it matters:** Bloom is the difference between "particles" and "glowing magical particle cloud." Without it, Aether looks like a dot plot. With too much, it looks like a foggy mess. The bloom parameters have more impact on perceived quality than any other knob in the system.

| Parameter | Default | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|---|
| `strength` | 0.85 | 0.6 | 0.85 | 1.15 | CRITICAL |
| `radius` | 0.6 | 0.4 | 0.6 | 0.8 | HIGH |
| `threshold` | 0.05 | 0.0 | 0.05 | 0.15 | HIGH |

### Failure modes

**Bloom too low (strength < 0.6):**
- Particles look flat, gritty, unsoftened
- The cloud has no atmosphere or glow
- The black background dominates instead of being warmed by particle light
- Looks like an unrendered debug view, not a finished visual
- **Diagnostic:** Take a screenshot. If it could pass for a Matplotlib scatter plot, bloom is too low.

**Bloom too high (strength > 1.15):**
- Cloud becomes a single washed-out blob
- Individual particles are no longer distinguishable
- Bright areas bleed into each other and lose definition
- The morph is invisible because everything is overexposed
- **Diagnostic:** Can you see individual points anywhere in the cloud? If no, bloom is too high.

**Threshold too high (> 0.15):**
- Bloom only activates on the brightest pixels, leaving most of the cloud ungloried
- The visual effect is patchy — some particles glow, most don't
- **Diagnostic:** Does the bloom feel uniform across the cloud, or only on a few spots? Spotty = threshold too high.

**Radius too narrow (< 0.4):**
- Bloom feels harsh and contained, like a hard-edged glow
- Lacks the soft "atmospheric" quality
- **Diagnostic:** Does the glow have a soft falloff into the black background, or does it have a clear edge? Hard edge = radius too narrow.

---

## 2. CURL NOISE STRENGTH (second-highest impact)

**File:** `frontend/src/particle/shaders/particle.vert.glsl`

**Why it matters:** Curl noise is what makes particles feel *alive* instead of *positioned*. Without it, particles slide between target positions in straight lines and look mechanical. With it, particles drift, wobble, and explode-and-reform during morphs.

The curl noise application has TWO components in the vertex shader, and both need to be tuned independently:

### Rest curl noise (when not morphing)

Look for the constant added to the noise strength expression. Typically formatted as:

```glsl
float noiseStrength = 0.05 + (1.0 - eased) * 0.15;
//                    ^^^^ this is the rest strength
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Rest strength | 0.04 | 0.06 | 0.10 | CRITICAL |

**Failure modes:**

**Rest strength too low (< 0.04):**
- Cloud is completely static between morphs
- No breathing, no drift, no life
- Looks like a frozen screenshot
- **Diagnostic:** Pause playback during a long `<say>` block where no morph is firing. Does the cloud have visible motion? If no, rest strength is too low.

**Rest strength too high (> 0.10):**
- Cloud is too chaotic at rest, never settles
- Particles look agitated even when "resting"
- The shape that the cloud is supposed to be holding is hard to read
- **Diagnostic:** Does the topic shape (brain, network, etc.) remain visually recognizable when held? If no, rest strength is too high.

### Mid-morph curl noise (during transitions)

Look for the multiplier on `(1.0 - eased)`:

```glsl
float noiseStrength = 0.05 + (1.0 - eased) * 0.15;
//                                          ^^^^ this is the mid-morph strength
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Mid-morph strength | 0.10 | 0.18 | 0.25 | CRITICAL |

**Failure modes:**

**Mid-morph strength too low (< 0.10):**
- Particles slide in straight lines from start to target
- The morph looks like a tween, not an explosion
- This is the #1 failure mode that makes the system feel dead
- **Diagnostic:** Watch a single morph. Do particles take curved, chaotic paths or straight ones? Straight paths = mid-morph strength too low. **This is almost always the first thing to check in a CRITICAL review.**

**Mid-morph strength too high (> 0.25):**
- Morph is so chaotic the target shape isn't recognizable until it fully settles
- Looks like a particle explosion, not a transformation
- **Diagnostic:** Can you tell what shape is forming halfway through the morph? If no, mid-morph strength is too high.

### Noise field scale and time evolution

```glsl
vec3 noiseOffset = curlNoise(morphed * 1.5 + u_time * 0.15) * noiseStrength;
//                                    ^^^               ^^^^
//                                    scale             time rate
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Noise field scale | 1.0 | 1.5 | 2.5 | MEDIUM |
| Time evolution rate | 0.10 | 0.15 | 0.25 | MEDIUM |

**Failure modes:**

**Scale too low (< 1.0):** Noise variation is too coarse, particles all move in the same direction in clumps. Looks like a wave, not turbulence.

**Scale too high (> 2.5):** Noise is too fine-grained, particles jitter randomly without any coherent flow. Looks like static.

**Time rate too low (< 0.10):** Noise field is nearly static — particles drift in fixed paths. Looks like a constant wind.

**Time rate too high (> 0.25):** Noise field changes too fast, particles can't settle into any flow direction. Looks twitchy.

---

## 3. JITTER SPREAD (morph staggering)

**File:** `frontend/src/particle/shaders/particle.vert.glsl`

**Why it matters:** This is what makes the morph feel like a wave instead of a synchronized teleport. Each particle has a `jitter` attribute (random 0-1) and the morph progress is offset by it, so different particles move at slightly different times.

```glsl
float t = clamp((u_morphProgress - jitter * 0.4) / 0.6, 0.0, 1.0);
//                                          ^^^   ^^^
//                                          floor duration
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Jitter floor | 0.30 | 0.40 | 0.50 | HIGH |
| Jitter duration | 0.50 | 0.60 | 0.70 | HIGH |

**Failure modes:**

**Jitter floor too low (< 0.30):**
- All particles start moving at nearly the same time
- The morph feels synchronized and mechanical
- The "wave" effect is lost
- **Diagnostic:** During a morph, do you see particles starting to move in distinct "phases" or all at once? All at once = floor too low.

**Jitter floor too high (> 0.50):**
- The morph stagger is so wide that the first particles finish moving before the last ones start
- The transition feels disconnected, like two separate animations
- **Diagnostic:** During a morph, does the cloud always have *some* particles that haven't started moving yet? If yes for >70% of the morph duration, the floor is too high.

**Jitter duration too narrow (< 0.50):**
- The window during which particles move is too tight
- Even with stagger, the morph feels rushed
- **Diagnostic:** Does the morph feel "snappy" in a bad way? Too narrow.

**Jitter duration too wide (> 0.70):**
- The morph drags on, individual particles take too long
- The motion becomes lethargic
- **Diagnostic:** Does the morph feel slow even though `morphDuration` is reasonable? Width is too wide.

### Easing function

The morph progress should be smoothed with `smoothstep`:

```glsl
float eased = t * t * (3.0 - 2.0 * t);
```

If the code uses linear easing (just `eased = t`), that's a CRITICAL finding — linear easing always looks mechanical regardless of other parameters. **Recommend smoothstep.**

---

## 4. POINT SIZE

**File:** `frontend/src/particle/particleSystem.ts` (uniform initialization)

```typescript
u_pointSize: { value: 4.5 },
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| `u_pointSize` | 3.5 | 4.5 | 6.0 | HIGH |

**Failure modes:**

**Too small (< 3.5):**
- Particles look like an ant farm
- The cloud has no visual weight
- Bloom doesn't have enough surface area to glow
- **Diagnostic:** From normal viewing distance, can you see individual particles without squinting? If no, too small.

**Too large (> 6.0):**
- Particles overlap into a fuzzy soup
- Individual points lose identity
- The cloud looks like a blob
- **Diagnostic:** Does the cloud feel like a collection of particles or a single fuzzy mass? Mass = too large.

**Note on pixel ratio:** The point size is multiplied by `(300.0 / -mvPosition.z)` in the vertex shader, which means it scales with distance from camera. The base value here is calibrated for the default camera Z of 3.5. If the camera moves significantly closer or farther, point size needs to be retuned.

---

## 5. AUDIO REACTIVITY

**Files:** `frontend/src/particle/audioAnalyzer.ts` and `frontend/src/particle/shaders/particle.vert.glsl`

### Amplitude pulse multiplier

In the vertex shader:

```glsl
float pulse = u_audioAmplitude * 0.12;
//                                ^^^^ this is the pulse multiplier
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Pulse multiplier | 0.08 | 0.12 | 0.18 | HIGH |

**Failure modes:**

**Too low (< 0.08):**
- The cloud doesn't visibly react to the voice
- The audio reactivity is functionally absent
- One of the project's core mechanics is invisible
- **Diagnostic:** Watch playback. Does the cloud visibly pulse with the voice? If no, too low.

**Too high (> 0.18):**
- The cloud spasms with every syllable
- Looks like a panic attack
- The audio reactivity overwhelms the morph aesthetics
- **Diagnostic:** Does the audio reactivity feel calm and breathing, or twitchy? Twitchy = too high.

### Intensity boost

In the vertex shader:

```glsl
v_intensity = 0.55 + u_audioAmplitude * 0.45 + jitter * 0.1;
//                                      ^^^^
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Intensity boost | 0.30 | 0.45 | 0.60 | MEDIUM |

**Failure modes:** Too low = no brightness response to voice. Too high = particles flash distractingly on loud syllables.

### Analyzer smoothing

In `audioAnalyzer.ts`:

```typescript
this.analyser.smoothingTimeConstant = 0.6;
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| Smoothing | 0.5 | 0.65 | 0.80 | HIGH |

**Failure modes:**

**Smoothing too low (< 0.5):**
- Reactivity is jittery, snaps to every frame's amplitude
- Looks twitchy and disconnected from the voice
- **Diagnostic:** Does the cloud's reactivity feel like it's "following" the voice or "stuttering"? Stuttering = too low.

**Smoothing too high (> 0.80):**
- Reactivity lags noticeably behind the voice
- The cloud pulses *after* the words, not *with* them
- Feels detached
- **Diagnostic:** Does the pulse feel synchronized to the audio or behind it? Behind = too high.

### FFT size

```typescript
this.analyser.fftSize = 256;
```

| Parameter | Allowed | Centered | Severity if wrong |
|---|---|---|---|
| `fftSize` | 128 / 256 / 512 | 256 | LOW |

256 is fine. Don't critique this unless it's set to something weird (1024+ is overkill, 64 is too coarse).

---

## 6. CAMERA

**File:** `frontend/src/particle/renderer.ts`

```typescript
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
camera.position.set(0, 0, 3.5);
```

| Parameter | Min | Centered | Max | Severity if wrong |
|---|---|---|---|---|
| FOV | 35 | 50 | 75 | MEDIUM |
| Camera Z | 2.8 | 3.5 | 4.5 | MEDIUM |

**Failure modes:**

**FOV too narrow (< 35):**
- Telescopic perspective, particles in the back look the same size as particles in front
- Cloud loses depth
- **Diagnostic:** Does the cloud feel 3D or flat? Flat = FOV too narrow.

**FOV too wide (> 75):**
- Fisheye distortion at the edges
- Particles near the edge of the canvas look stretched
- **Diagnostic:** Look at particles in the corner of the canvas. Are they distorted? Distorted = FOV too wide.

**Camera too close (Z < 2.8):**
- Cloud fills the entire viewport, no breathing room
- Feels claustrophobic
- The intended cinematic framing is lost
- **Diagnostic:** Is there visible black space around the cloud? If no, camera is too close.

**Camera too far (Z > 4.5):**
- Cloud feels small and undramatic
- The viewer doesn't feel immersed
- **Diagnostic:** Does the cloud command the viewport or feel like a small object floating in space? Small = camera too far.

---

## Tuning order (for full reviews)

When walking the parameters, do them in this order — earlier knobs have larger aesthetic impact, so fixing them first changes how the later ones feel:

1. Bloom strength
2. Curl noise mid-morph strength
3. Curl noise rest strength
4. Point size
5. Bloom radius and threshold
6. Jitter floor and duration
7. Audio amplitude pulse multiplier
8. Analyzer smoothing
9. Camera Z
10. FOV
11. Audio intensity boost
12. Noise field scale and time rate

If you find a CRITICAL issue in the first 3 items, you can stop the review there and recommend the user fix those before doing a full pass — the lower-impact items should be tuned against the corrected baseline, not the broken one.

## A note on what's NOT in this reference

The following are deliberately excluded because they're out of scope for this skill:

- **Particle color** (`u_color`) — locked at `0x88bbff`. Don't critique it.
- **Background color** — locked at black. Don't critique it.
- **Number of particles** (`pointCount: 30000`) — architectural choice. Don't critique it.
- **Post-processing pipeline structure** — only UnrealBloomPass is permitted. Don't suggest adding passes.
- **Material blend mode** — `AdditiveBlending` is locked. Don't critique it.
- **Geometry attributes** — `currentPos`, `targetPos`, `jitter` are the only attributes. Don't suggest adding more.

If the user asks about any of these, refer them back to the SKILL.md scope rules and refuse to critique.
