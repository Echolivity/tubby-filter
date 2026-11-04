> **Superseded for 2.2:** this is the V2.1 document, kept for reference. For 2.2.0-rc1 use `validation/ABLETON_LIVE_12_QA.md` and `validation/V22_RELEASE_READINESS.md`.

# Release checklist — Tubby Filter 2.1.0

The legend is **PASSED** / **FAILED** / **NOT PERFORMED** / **MANUAL (Live)**. "Passed" here always means passed at the stated level: [sim] = the shipped source run by GSX.

## Acceptance criteria from the V2.1 brief

| Criterion | Status | Evidence |
|---|---|---|
| Discrete parameter transitions are click-free | **PASSED [sim]**, **MANUAL (Live)** L4 | Every single switch is ≤ −70 dBFS at 4 rates (36 tests). Rapid Drive Cal toggling at 40 Hz reaches −69.6 dBFS. |
| Click/Glide behaviour consistent and documented | **PASSED [sim]**, **MANUAL (Live)** L12 | Same level at Glide 0–2000; never fires on mode change, load or rate change. DSP_ARCHITECTURE §6. |
| Frequency response validated across supported rates | **PASSED [sim]**, **NOT PERFORMED [live]** (capture cases C02–C04) | ≤ 1.01 dB at 44.1–192 kHz (was 4.48 dB). |
| Aliasing characteristics measured | **PASSED [sim]**, **NOT PERFORMED [live]** (C07) | MEASUREMENTS_V21 §D. |
| Numerical stability tests pass | **PASSED [sim]** | NaN/Inf, parameter corners, per-sample automation, DC, denormals, rate change, re-activation. |
| Python and gen~ outputs compared | **PARTIAL.** Python model vs shipped source: **PASSED** (bit-exact). Python vs compiled gen~: **NOT PERFORMED** | Needs the Live capture run (Part 1 of LIVE_VALIDATION). |
| Ableton integration tested or explicitly marked unverified | **Marked unverified** | LIVE_VALIDATION.md L1–L15, all NOT PERFORMED. |
| No V2 functionality unintentionally broken | **PASSED [sim]** for DSP; UI **MANUAL** L6–L8 | V2.1 equals V2 within 1e-12 where no oversampling runs. Harmonics within 0.001 dB. All parameter names kept. |
| Final .amxd reproducibly built from source | **PASSED** | Two builds are byte-identical, the shipped file equals a fresh build, and the source embedded in the .amxd equals `src/` (tests). The container layout also parses with Ableton's `maxdiff/amxd_textconv.py`. |

## Tests by status

**PASSED (automated, [sim]):** 90 / 90 pytest tests. One of them self-tests the capture comparison tool (a perfect render passes; a 0.2 dB gain error fails).

**FAILED:** none open. Failures found during development and fixed:
- Mono lost bit-exactness after a crossfade was added.
- Re-activation produced a muted dip.
- A measurement script joined L and R before filtering.
- The capture tool checked latency in only one case.

**NOT PERFORMED:**
- Compiling the source in gen~ and checking the Max console (L1).
- All 36 capture renders (12 cases × 3 rates) compared against the reference.
- Real CPU and load time (L13, L14).

**MANUAL (Live) required:** L1–L15 in `validation/LIVE_VALIDATION.md`.

## Before tagging 2.1.0 as released
1. L1: the device loads and gen~ compiles with no console errors. **If gen~ rejects any construct** (for example multiple-return assignment inside `if`), fix it in `src/`, rebuild, and re-run `pytest`.
2. Part 1 capture comparison at 44.1, 48 and 96 kHz: all cases PASS.
3. L2–L15 completed, with results written into LIVE_VALIDATION.md.
4. `git tag v2.1.0`.

Current state: **steps 1–4 open. Do not distribute as a release.**
