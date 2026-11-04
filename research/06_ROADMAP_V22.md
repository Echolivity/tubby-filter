# Proposed V2.2 roadmap

**Principle:** one meaningful improvement, done properly, rather than several features. V2.2's identity is **a filter that responds to how it is played.**

## Gate 0 — Prerequisite: validate V2.1 natively (blocks everything)
- Run L1–L15 and the capture kit on the **V2.1 release candidate** first. Every V2.2 change is measured against V2.1, so the baseline must be proven in gen~ and Live.
- **If gen~ rejects a construct**, fix it in V2.1 first (patch release 2.1.1), and re-run the full simulated suite and the capture kit.

## Milestone 1 — Motion (the V2.2 feature)
**Status:** candidate built and [sim]-validated (`experiments/candidate/`).

1. **Listening.** Blind ABX of `A_v21` vs `C_motion` and `E_core_motion`, with at least 3 listeners, on the sweep and step bars.
   - **Go:** a consistent preference for Motion, or a clear "different and useful".
   - **No-go:** keep it in research.
2. **Tune by ear, within measured limits.** The constants are the 8 oct/s half-point, the 2 ms attack, the 120 ms release and the ×5 maximum Q factor. Any change re-runs `pytest experiments`, where every threshold is a fixed acceptance criterion.
3. **Native validation of the candidate.**
   - Capture kit at Motion 0 (must equal V2.1).
   - A Motion capture case.
   - CPU Reporter: Motion must cost ≤ 10 % over V2.1 at 44.1/48/96 kHz.
4. **Merge** `experiments/candidate/*.genexpr` into `src/`. Promote the candidate tests into `tests/`. Update the docs and the manual. Bump to 2.2.0.

**Backward compatibility:**
- New parameter `Motion`, range 0–100 %, default 0. It does not change the default, ID, range or meaning of any existing parameter.
- At 0, output is bit-identical to V2.1 ([sim] tested at 4 rates).
- V2/V2.1 sets and presets load with Motion at its default 0, so they sound unchanged. This needs a Live check.

## Milestone 2 — Latency reporting (engineering)
- Set *Defined Latency* = 3 samples and add the constant 3-sample delay at ≥ 60 kHz (X7).
- **Go only if L15 shows Live compensates it.** Expected result: parallel null at 1 kHz improves from −7 to −40 dB at 44.1/48 kHz.
- Then document that the remaining high-frequency mismatch comes from the IIR oversampler's phase.

## Milestone 3 — Documentation-only wins (no DSP)
- **Manual:** "Reso 1.0 + 18 dB ≈ the original Altec/KTBK passive response", measured within 0.1 dB of a 3rd-order Butterworth (hypothesis stated).
- **Manual:** "Mix around 50 % gives moving phasing": a −9 to −14.5 dB cancellation at about 0.85 × the step frequency.
- **Manual:** put Tubby *before* the echo or reverb send, as on the desk.
- **Optional UI:** a marker at Reso 1.0.

## Research backlog (not scheduled)

| Item | Next step | Decision gate |
|---|---|---|
| X1 Core (non-linear inductance) | Listening vs Drive at matched THD | Keep only if listeners hear the cutoff-localised character as distinct from Drive |
| X3b Inductive-kick click | Listening; decide whether it is a Click *character* (a compatibility question) | Must not change the sound of V2 sets at their saved Click value |
| X2d Motion direction weighting | Listening, once Motion is accepted | Expose only if it clearly adds expression |
| X4 Vari-notch | Revisit only if Mix phasing proves insufficient | — |

## Rejected (with reasons in 04_EVALUATION_MATRIX.md)
- True hysteresis on the cutoff.
- The break-before-make gate.
- Separate Bell and 600 modes.
- Tolerance variation.
- Linear-phase FIR or 4× oversampling.
- LFO, envelope follower and soft clip.

## Branching
- `main` stays at `v2.1.0-rc1` and is not touched.
- `dev/v2.2-research` holds all research: experiments, candidate, reports, and the test-infrastructure fix.
- After Gate 0, the infrastructure fix and the added V2.1 tests (Part 7) can be cherry-picked to `main`. They change no DSP and no device file.
- After Milestone 1's go decision, cut `release/2.2`.
