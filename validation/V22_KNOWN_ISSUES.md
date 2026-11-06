# Tubby Filter 2.2.0-rc1 — known issues and unresolved items

Every item is either a measured characteristic (**[sim]**: the shipped source run by GSX), a validation gap (**BLOCKED**: needs Max or Live), or a decision that needs a human listener.

## Open: must be resolved before release

| ID | Area | Issue | Evidence | Proposed resolution |
|---|---|---|---|---|
| **KI-02** | gen~ | **Native compilation has not been performed.** The source uses 14 multiple-return assignments (`a, b, … = f(…)`) inside `if/else` blocks. This is a documented GenExpr feature, but its use inside a block isn't confirmed, and nothing else in the static audit is uncertain. | `tools/gen_compat.py` reports no issues apart from this note. | **L1** in the QA checklist. If gen~ rejects it, compute both branches and select with `?:` (no DSP change, more CPU at ≥ 60 kHz), and re-run every test. |
| **KI-01** | Motion | **A faint transient on hard steps.** With Motion 100 %, a hard (Glide 0) step adds about **−54 dBFS above 3 kHz** for a −12 dBFS input, 42 dB below the signal. It comes from the 2 ms bloom attack changing the damping quickly. It is ≥ 15 dB below the device's own default Click (30 %) on the same step, so it is masked at default settings. | Strict xfail `test_M13`; bound test `test_M13b`. Attack trade-off, all [sim]: 2 ms gives −53.5 dBFS / +3.7 dB step bloom; 5 ms −61.2 / +2.5; 10 ms −67.2 / +1.6; 20 ms −73.1 / +0.9. Sweep bloom is unchanged (+4.1–4.2 dB). | **Listening decision.** Compare `reports/v22/audio/KI01_*` (attack 2, 5 and 10 ms) at Click 0. Keep 2 ms if the tick is inaudible in context, otherwise pick 5 or 10 ms, accepting less bloom on hard steps. |
| **KI-03** | Latency | At 44.1 and 48 kHz the oversampler delays the signal by **about 3.07 samples at low frequencies, rising to 7.9–10.2 samples at 18 kHz.** Live is not told about it. Summing with an uncompensated parallel dry copy partly cancels from about 1 kHz up. A 3-sample *Defined Latency* would improve the null at 1 kHz from −7 to −40 dB, but **no integer delay is right across the band** (best integer per band in `reports/v22`). | `test_L01`; `reports/v22/v22_measurements.json` → `latency_phase` | **Not implemented**, as the brief asks: no hard-coding from simulation. PDC behaviour is test **L-PDC-1/2** in the QA checklist. The decision follows those results. |
| **KI-06** | Presets | Old V2.1 sets and presets don't contain `Motion`. Live is *expected* to apply the parameter's initial value, 0, which gives V2.1's sound. Not verified in Live. | `test_P04` shows Motion 0 is bit-exact with V2.1 [sim]. | QA **P-1 to P-3**. |

## Compatibility change (rc5)

| ID | Change | Why | Risk / check |
|---|---|---|---|
| **KI-08** | **Filter** and **Filter R** changed from Enum (12 items) to **Float 0–11**, snapped to the nearest step by the DSP. Range, default (0 = FLAT), long names and stored numeric values are unchanged. The step name is shown by a label (FLAT … 10k). | Reported from Live 12: Live's LFO in **Mod** mode can't map Enum parameters ("The selected parameter does not support this operation"). Live only modulates Float parameters. | Old V2/V2.1 sets and automation of *Tubby Filter* hold the values 0–11, so they should land on the same step. **Unverified in Live.** QA items A-2 and P-2. |

## Characteristics: documented behaviour, not defects

| ID | Characteristic | Evidence |
|---|---|---|
| KI-04 | **Tonal content sitting on a fast-moving resonance gets louder.** A 300 Hz tone during a 500 ms glide gets +9.75 dB louder 50 ms after Motion jumps to 100 %. On program material (pink noise) a hard step adds +3.7 dB (20 ms loudness) at Reso 1.4 and +4.6 dB at Reso 8; peaks rise by up to +3.1 dB. The +6 dBFS safety knee still applies. | `test_M15`, `motion.hard_step_*` in the measurements |
| KI-07 | **Motion fades exponentially rather than switching off.** The glide is a one-pole, so the cutoff never stops exactly, and the bloom decays with the 120 ms release: about −20 dB at 0.3–0.4 s and below −60 dB by 1 s after a hard step. After a slow glide it stays partly active while the cutoff is still moving, which is by design. | `test_M04`, `test_R10` |
| KI-11 | Inherited from V2.1, all unchanged: aliasing at extreme drive on very high tones; the 10 kHz step deviates up to 1.0 dB from the analog prototype; Unity calibration compresses loud material; a one-sample hand-over when the sample rate changes. | V2.1 reports; V2.2 is bit-identical at Motion 0 |

## V2.1 issues found during this audit (V2.1 left untouched)

| ID | Issue | In V2.2 |
|---|---|---|
| KI-05a | V2.1's source uses variable names `f` and `i`, which are gen operators (`f` float, `i` int). Native compilation might reject them or shadow the operators. | Renamed to `hpf` and `idx`. Bit-identical output (tested). |
| KI-05b | V2.1's Live Info View texts for Glide and Click still describe the V2 rule ("hard-switch mode only", "no transient"), which contradicts V2.1's own Click/Glide behaviour. | Corrected texts. |
| KI-05c | If KI-05a stops V2.1 compiling natively, V2.1 needs a 2.1.1 patch. Do not edit `legacy/v2.1`; branch from tag `v2.1.0-rc1`. | — |

## Found and fixed in 2.2.0-rc1 (relative to the research candidate)

| ID | Defect | Fix | Evidence |
|---|---|---|---|
| FX-01 | The bloom after a hard step lasted about 0.6 s at full strength, instead of the documented 120 ms release, because the envelope followed *raw* speed (about 2000 oct/s) before it was saturated. | Map the speed to 0..1, *then* apply the 2/120 ms envelope. | Bloom −20 dB at about 300 ms (candidate: about 0 dB at 400 ms). High-frequency content added by a hard step improved from −29.9 to −53.5 dBFS. Sweeps unchanged (+4.23 against +4.24 dB). |
| FX-02 | gen name collisions `f` and `i`. | Renamed. | `test_G01` |
| FX-03 | Outdated Glide/Click help texts. | Corrected. | `test_P01` (info excluded); visible in `device/*.maxpat` |
| FX-04 | The research candidate device still carried the gen~ title `tubby_v2_1` and EXPERIMENTAL labels. | Release build: `tubby_v2_2`, version 2.2.0-rc1 everywhere. | `test_B02` |

## Validation gaps (BLOCKED in this environment)
- Native gen~ compilation, device loading, and any Ableton Live behaviour.
- Audio playback and listening (the VM has no audio device), so **no audio was listened to.**
- Real CPU measurement (the figures here are proxies).
- An Ableton `.als` test project was **not** generated. A Live 12 set can't be checked for validity without Live, and delivering an untested set would risk a misleading result. Building one by hand takes about 5 minutes; see `ABLETON_LIVE_12_QA.md` §0.
