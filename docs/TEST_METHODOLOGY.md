# Test methodology

V2.1 is checked at three levels. Each level can only vouch for what it actually executes, and every result in this project carries a label saying which level produced it.

| Level | What runs | Label | Proves | Cannot prove |
|---|---|---|---|---|
| 1. Reference model | `tests/model_v21.py`, hand-written from the spec | **[ref]** | That the specification behaves as intended | Anything about the shipped code |
| 2. Source execution | The shipped `src/tubby_filter.genexpr`, parsed and run by `tools/gsx.py` | **[sim]** | That the shipped source implements the spec. Every [sim] number comes from the real source text, not a port. | What Cycling '74's gen~ compiler produces, gen~'s float handling, or Live's host behaviour |
| 3. Device in Live | `device/Tubby Filter.amxd` rendered by Ableton Live, compared by `validation/compare_capture.py` | **[live]** | The compiled device itself | — |

**Current status: levels 1 and 2 have been run; level 3 has not been run** (no Max or Live was available). No [sim] result in this repository is presented as evidence of gen~ or Live performance.

## Level 1 ↔ 2 cross-check
`tests/test_regression.py::test_model_matches_source_bit_exact` runs the hand model and the shipped source on the same random input and random per-block automation of all 13 parameters. It then requires **bit-identical** output, so it fails on any difference at all. The check passes at 44.1 and 96 kHz in the suite, and separately at 44.1, 48, 88.2, 96 and 192 kHz including sample-rate switching and device on/off.

This cross-check also found a real V2 discrepancy. V2's source initialised its frequency state to `2.9957` while the specification uses `log(20) = 2.995732…`, which gave an output difference of up to 3.3·10⁻⁶. V2.1 uses the exact value.

## GSX: what it implements
GSX is a small GenExpr-to-Python compiler (numba) covering the subset this project uses: `Param`, `History`, functions, multiple returns, `if/else`, `for`, `?:` and the built-ins listed in `tools/gsx.py`. It follows these documented gen~ semantics:
- Functions are inlined; a `History` inside a function gets separate state per call site.
- `Param` values are clamped to their declared min/max.
- Comparisons return 1/0, and both branches of `?:` are evaluated.
- Variables first assigned inside an `if`/`for` block are local to that block.

GSX also rejects two kinds of code instead of guessing their meaning:
- **Read-after-write History.** A History that is read after being written in the same frame is a compile error. gen~'s documentation doesn't define this case, so the shipped code is written never to need it.
- **Unknown built-ins**, which are rejected outright.

Known differences from gen~:
- `noise()` uses a different random sequence, so Level 3 compares the switch transient by level, not sample by sample.
- `fixdenorm` flushes below the single-precision limit, which is the stricter choice.
- gen~ is believed to compute in 64-bit double inside Max. If it doesn't, Level 3 will show errors around −140 dBFS, which is well inside the −80 dBFS tolerance.

## Level 2 suites
- `tests/test_regression.py` (pytest, 90 tests, about 1 minute) covers the acceptance criteria:
  - Discrete switches at 4 rates must stay at or below −70 dBFS of content above 3 kHz.
  - Click/Glide rules.
  - Frequency response within 1.1 dB of the analog prototype at 6 rates.
  - Oversampler passband within 0.01 dB to 20 kHz.
  - Aliasing must improve by at least 15 dB over V2.
  - Stability under NaN/Inf, parameter corners, per-sample automation, out-of-range values, DC, rate change and re-activation.
  - Stereo, calibration within 0.02 dB, a reproducible build, the .amxd container layout and its embedded source, and UI/DSP parameter coverage.
  - **V2 preservation**: at 88.2, 96 and 192 kHz (no oversampling), V2.1 output equals V2 output within 10⁻¹² for static settings.
- `tests/measure_v21.py` produces the full report in `reports/`. `tests/baseline_v2.py` is the measure-before-change run on V2.

## Metrics
- **Transition artefact**: peak of a 4th-order 3 kHz high-pass of the output within 30 ms after a switch, with a 100 Hz −12 dBFS input. Anything above 3 kHz is artefact.
- **Aliasing**: a bin-centred sine with a Blackman-Harris window. Energy below 20 kHz that is not the fundamental, a harmonic or DC is counted as alias, and reported relative to the fundamental.
- **Frequency-response error**: impulse response compared with the analog prototype (2-pole HP, plus 1-pole for 18 dB). Reported separately for f ≥ fc (cutoff, peak and passband) and for the skirt from fc down to −20 dB, up to min(20 kHz, 0.4·fs).

## CPU
Every CPU figure in this repository is a **proxy**: the GSX-compiled source timed on the development machine. It shows *relative* cost (V2.1 vs V2, scaling with rate and instances), not gen~ or Live load. Real CPU is test L13 in `validation/LIVE_VALIDATION.md`, using Ableton's CPU Reporter.
