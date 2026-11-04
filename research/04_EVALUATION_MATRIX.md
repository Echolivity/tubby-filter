# Feature evaluation matrix

**Scales.**
- **Benefit columns** (sonic, musical): 1 = negligible, 5 = strong. Sonic benefit rests on measurements. *Musical usefulness is my judgement from the references and measurements; it has not been listened to.*
- **Cost columns:** **L** = low, **M** = medium, **H** = high burden.
- **Compatibility:** "none" means V2 and V2.1 sets sound identical with the feature at its default.

| # | Proposal | Sonic benefit | Musical usefulness | Technical complexity | CPU overhead | Latency | Stability risk | Compatibility | Class |
|---|---|---|---|---|---|---|---|---|---|
| X2 | **Motion**: resonance blooms with cutoff speed | 4: up to +4.7 dB ring energy, 4× longer decay mid-sweep; +7.4 dB bloom after a step; no change at rest | 5: answers the "respond to movement" question; aimed at performed sweeps | L: about 25 lines of gen code, no new state topology | L: 0–15 %, within noise | none | L: stable at Q 8 × 5; no self-oscillation | none: new control, default 0 = bit-exact V2.1 | **IMPLEMENT** (candidate; pending listening + native gen~) |
| X7 | Declared latency 3 samples + constant-latency option at ≥ 60 kHz | 3: parallel null at 1 kHz goes from −7 to −40 dB at 44.1/48 | 3: matters for parallel and multi-track setups | L | L | +3 samples at ≥ 60 kHz (0.03 ms) | L | none | **IMPLEMENT** (conditional on Live verifying compensation, test L15) |
| X5 | Document Reso 1.0 + 18 dB ≈ the 3rd-order passive response | 2: within 0.1 dB of Butterworth-3 | 3: gives users the "original" setting | L (docs) | none | none | none | none | **IMPLEMENT** (docs) |
| P | Document Mix-50 % phasing (−9 to −14.5 dB moving dip) | 2 | 3 | L (docs) | none | none | none | none | **IMPLEMENT** (docs) |
| X1 | Core: non-linear inductance (both variant) | 4: distortion confined to about ±1 octave of the cutoff; clean passband; resonance self-compresses 3–4 dB at 0 dBFS | 3: distinctive, but overlaps Drive; not authentic (KTBK THD < 0.01 %) | M: needs careful scaling; interacts with Reso and Drive | L–M: 0–15 % | none | L: tested stable at extremes | none if it is a new control defaulting to 0 | **EXPERIMENT** |
| X3b | Signal-dependent switch transient (inductive kick) | 3: louder on bass near the cutoff, silent on silence, matches the KTBK note | 3: more physical clicks | L | L | none | L | **M:** the natural home is the Click control, which would change V2 sets' sound unless added as a selectable character | **EXPERIMENT** |
| X2d | Motion direction weighting | 2: falling sweeps −10 dB less bloom at full weighting | 2: no physical justification | L | L | none | L | none if fixed internally | **EXPERIMENT** (not exposed) |
| X2h | True hysteresis (play operator) on the cutoff | 2: ±1/8 octave offset depending on approach direction | 1: makes the stepped resting cutoff unpredictable | L | L | none | L | none | **REJECT** |
| X3a | Break-before-make gate transient | 1: loudest on treble, the opposite of the hardware | 1 | L | L | none | L | — | **REJECT** |
| X4 | Vari-notch mode | 2: depth −8 to −20 dB rising with step | 2: Mix 50 % already gives a moving dip; pushes towards multimode | M | L | none | L | new mode | **REJECT** (for V2.2) |
| — | Separate Bell / 600 modes | 1: already covered by Reso | 1 | M | L | none | L | new mode | **REJECT** |
| X6 | Component-tolerance variation | 1 | 1: less predictable; breaks Link's bit-identical L/R | L | L | none | L | breaks a tested guarantee | **REJECT** |
| — | Linear-phase FIR oversampling | 2: perfect parallel null | 2 | M | M: about 63 taps | **+31 samples** | L | none | **REJECT** |
| — | 4× oversampling | 1: no measured need short of extreme drive at 15 kHz | 1 | M | M–H | more | L | none | **REJECT** |
| — | LFO / envelope follower / soft clip (AudioThing) | — | 2: Live already provides these | M | L | none | L | adds controls | **REJECT** (out of identity) |

## Why Motion and not Core is the V2.2 focus
- **The brief's central question is about movement.** Motion is the only proposal that makes the filter respond to *how* it is played, and it is measurable: same position, different resonance depending on speed.
- **It is invisible until used.** At rest nothing changes, and at 0 everything is bit-identical to V2.1, so it can't damage the established sound.
- **Core is distinctive but competes with Drive** for the "add harmonics" role. Its strongest argument, distortion localised at the cutoff, needs a listening test to show it is worth a second saturation control.
