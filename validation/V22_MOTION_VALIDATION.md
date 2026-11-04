# Motion validation — 2.2.0-rc1

**Environment:** [sim], the shipped source executed by GSX on Linux (see the environment note at the top of V22_COMPARISON_REPORT.md). 48 kHz unless stated. Sources: `reports/v22/v22_measurements.json` (`motion`) and `tests/test_v22.py` (M-tests).

**Listening: NOT PERFORMED.** This VM has no audio device. Every statement here is a numerical measurement; nothing has been heard. The audio for a listener is in `reports/v22/audio/` (§4).

## 1. Intended behaviour against what was measured

| Intended | Test | Result |
|---|---|---|
| Responds to cutoff movement speed | M03a | Bloom (impulse ring energy, Motion 100) by glide time: 2000 ms **+0.34**, 1000 ms **+1.25**, 300 ms **+4.23**, 100 ms **+6.46**, 50 ms +5.75, 20 ms +6.40 dB. It rises with speed and saturates near +6.5 dB, as the mapping speed/(speed+8) approaches 1. **PASS** |
| Scales with the amount | M03b | Glide 300 ms: Motion 25/50/100 gives +1.34 / +2.47 / +4.23 dB. **PASS** |
| Preserves the cutoff trajectory | M12 | The internal log-cutoff, exposed by instrumenting the source, is **bit-identical** at Motion 0 and 100 for Glide 0, 40 and 400 ms. **PASS** |
| Transient bloom on fast movement | M02, M03, M04 | Hard step, pink at −18 dBFS: 20 ms loudness **+3.7 dB** (Reso 1.4), +5.3 dB (Reso 4), +4.6 dB (Reso 8); peaks +1.8 / +2.8 / +3.1 dB. **PASS** |
| Decays naturally after movement | M04, R10 | Bloom relative to the output after a hard step: −10.7 dB at 0.1 s, −21.5 at 0.3 s, −43.6 at 0.6 s, −71.5 at 1 s and −108.7 dB at 1.5 s (Reso 1.4). That is an exponential decay at the 120 ms release. **PASS** |
| No effect at Motion 0 | R01–R11 | Bit-identical to V2.1 (35/35 report cases plus the suite). **PASS** |
| No modulation at a stationary cutoff | M11, capture C13 | Motion 100, automated 0 → 100 ramps, or random Motion at a static cutoff are all **bit-identical** to Motion 0. **PASS** |
| No unstable or excessive resonance | M09, S01, M05 | The peak rises by ≤ +3.1 dB at Reso 4 and 8. Every step still rings down below −120 dBFS within 1 s at Reso 8 with Motion 100 (no self-oscillation). Repeated steps every 150 ms give +1.69 dB RMS and +1.61 dB peak, with no build-up (last second against the second second: +0.13 dB). **PASS** |

## 2. The ten required scenarios

| # | Scenario | Measurement | Status |
|---|---|---|---|
| 1 | Slow sweep (Glide 2000) | +0.34 dB bloom: subtle | PASS (M01) |
| 2 | Medium sweep (Glide 300) | +4.23 dB | PASS (M02) |
| 3 | Fast sweep (Glide 50) | +5.75 dB | PASS (M03) |
| 4 | Abrupt jumps (Glide 0) | +3.7 dB loudness; −21.5 dB at 0.3 s. **High-frequency content added on the step: −53.5 dBFS (KI-01)** | PASS (M04); **FAIL** against the −70 dBFS click criterion (M13, strict xfail, KI-01) |
| 5 | Repeated movements | +1.69 dB RMS, no accumulation | PASS (M05) |
| 6 | Up and down sweeps | Up +4.23 dB, down +4.91 dB: near-symmetric, no direction bias by design | PASS (M06) |
| 7 | Near minimum cutoff | FLAT → 70: +2.24 dB; 70 → 100: +2.72 dB (Reso 8); peak increase < 6 dB | PASS (M07) |
| 8 | Near maximum cutoff | 7.5k → 10k, Reso 8: Q ×2.88, +5.6 dB loudness, +3.0 dB peak (the ring metric over-reads here; see D8); bounded at 44.1, 96 and 192 kHz | PASS (M08) |
| 9 | High resonance | Reso 4 and 8: peak +2.8 / +3.1 dB; rings down; no self-oscillation | PASS (M09, S01) |
| 10 | Rapid automation | A new random step and a new random Motion value every sample at 44.1 and 192 kHz: finite and bounded | PASS (M10) |

## 3. Character assessment (from numbers, not listening)
- **Bloom character:** the bloom is a raised Q at the moving cutoff, at most ×5 and typically ×3–4.6 for performed moves. It sits only around the moving edge (`img/motion_sweep_spectrogram.png`). The level rises are moderate on program material (+2 to +6 dB, 20 ms loudness) and largest on tonal content that sits on the resonance (KI-04: a 300 Hz tone gets +9.75 dB louder).
- **Transient response:** the 2 ms attack follows hard steps closely enough to bloom (+3.7 dB). That speed is also what produces the small high-frequency transient (KI-01). An attack of 5–10 ms trades less tick for less bloom; see the KI-01 renders.
- **Clicks and discontinuities:** mode switches, slope, Drive Cal and Drive-only switching stay below −70 dBFS with Motion 100 at 44.1 and 96 kHz (M14). An instant Motion change mid-glide adds −81 dBFS above 3 kHz (M15). The only exception is KI-01.
- **Unnatural frequency movement:** none. The trajectory is bit-identical (M12).
- **Recovery:** exponential at the 120 ms release; below −100 dBFS within about 1.5 s (M04, R10).
- **Not made more extreme.** No constant was changed to enlarge the effect. The rc1 fix (FX-01) made the hard-step bloom *shorter and smaller*, which is the documented behaviour.

## 4. Audio for listening (`reports/v22/audio/`, 48 kHz, 32-bit float)

| File | Content |
|---|---|
| `ref_dry_dub_loop_48k.wav` | The dry test loop: 32 beats at 76 BPM of kick, rim, hats, skank and bass |
| `ref_v21_dub_loop_48k.wav`, `ref_v22_motion0_dub_loop_48k.wav` | V2.1 and V2.2 at Motion 0 with the same performed Filter automation (steps, then 250 ms glides) |
| `null_v22_motion0_minus_v21_48k.wav` | Their difference: digital silence (peak 0.0) |
| `demo_motion050/100_dub_loop_48k.wav` | The same performance at Motion 50 and 100 (unmatched) |
| `…_levelmatched.wav` | RMS-matched to V2.1 (−0.23 / −0.42 dB) for fair comparison |
| `demo_sweeps_pink_glide300_motion000/100.wav` | 300 ms glides on pink noise |
| `demo_hardsteps_loop_reso6_motion000/100.wav` | Hard steps, Reso 6, Click 30 |
| `KI01_hardsteps_click0_motion000.wav`, `…motion100_attack02ms/05ms/10ms.wav` | KI-01 decision material: hard steps, Click 0, Reso 4 |
