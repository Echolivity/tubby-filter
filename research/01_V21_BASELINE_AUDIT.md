# V2.1 baseline audit

Audited: tag `v2.1.0-rc1` (commit 64b119e), on branch `main`, which is unmodified. All V2.2 work is on `dev/v2.2-research`.

## 1. Source tree and authority

| Path | Role | Authoritative? |
|---|---|---|
| `src/tubby_filter.genexpr` | The DSP, one gen~ codebox | **Yes. This is the single source of truth.** |
| `src/build_device.py` | Generates the patcher and the .amxd from the source, deterministically | Yes, for the device |
| `device/Tubby Filter.amxd`, `.maxpat`, `build_manifest.json` | Build outputs | Derived; a test checks they match a fresh build |
| `tests/model_v21.py` | Hand-written reference model | Derived from the spec; bit-exact with the source |
| `tools/gsx.py` | Independent GenExpr executor | Test tool; **not** gen~ |
| `tools/halfband.py` | Oversampler coefficient design | Design tool |
| `tests/test_regression.py`, `measure_v21.py`, `baseline_v2.py`, `metrics.py` | Tests and measurements | — |
| `validation/` | Live capture kit and checklist | — |
| `legacy/v2/` | Frozen V2 source (hash-pinned), docs, scripts | Historical |

## 2. Simulated versus native execution

| Execution path | Exists here | What it is |
|---|---|---|
| Hand reference model (numba) | Yes | Independent implementation of the spec |
| GSX execution of the shipped `.genexpr` | Yes | Independent compiler of the GenExpr subset used |
| Native gen~ compilation (Cycling '74) | **No. BLOCKED** | No Max installation available |
| Device running in Ableton Live | **No. BLOCKED** | No Live installation available |

Every V2.1 number that has ever been published is simulated, meaning it came from GSX or the model.

## 3. Reproduced results (this session)

| Check | V2.1 claim | Reproduced |
|---|---|---|
| Regression suite | 90/90 pass | **90/90 pass** (91.5 s before the infrastructure fix, 40.5 s after) |
| Model ↔ source bit-exact | yes | yes (part of the suite) |
| Build reproducible; shipped .amxd = fresh build | yes | yes (part of the suite) |
| Experiment model with experiments off ↔ V2.1 model | n/a | **bit-identical** at 44.1 and 96 kHz with random steps, stereo modes, drive, glide and click |

**Slow tests investigated.** Three tests took 22–28 s each. The cause was a second numba JIT compilation of identical code, triggered by passing a read-only broadcast array, which numba treats as a different type. The fix passes writeable arrays and caches compiled programs. **No test or tolerance changed.** The suite now takes 40.5 s, of which about 26 s is the unavoidable first compile.

## 4. Implementation review findings

1. **The DSP is sound and well tested at the simulation level.** It meets every V2.1 acceptance item that can be checked here.
2. **GenExpr portability risk (unverified).** The source assigns several returned values at once (`a, b, c = f(...)`) inside an `if` block, and declares 59 History states (more at run time, because each call site of `slew()` and `xfade()` gets its own state). Both are documented GenExpr features, but neither has been compiled by gen~. This remains the single largest technical risk.
3. **Latency.** The oversampler adds about 3.1 samples of group delay at 1 kHz (44.1/48 kHz host rate) and none at 88.2 kHz and above. Max for Live devices can declare a fixed latency through the patcher's *Defined Latency* attribute ([Cycling '74 docs](https://docs.cycling74.com/max7/vignettes/live_audiodevices)). V2.1 doesn't, and a single fixed value would be wrong at either 44.1/48 or 88.2+. See experiment X7.
4. **No user-facing defects found** in the docs or the code. The documentation matches the source: every parameter, range, default and Click/Glide rule was cross-checked against the code in the suite.

## 5. Known limitations carried into V2.2 (from V2.1 docs, all still true)
- Unreported latency at 44.1 and 48 kHz.
- Aliasing at extreme drive on very high tones (−18 dB for a 15 kHz tone at Drive 100 %, 44.1 kHz).
- The 10 kHz step deviates up to 1.0 dB from the analog prototype.
- Unity drive calibration compresses loud material.
- A one-sample hand-over when the sample rate changes.
- Nothing has been verified in gen~ or Live.

## 6. Reproducible measurement baseline
- **Signals.** All test signals are generated in code from fixed seeds (`default_rng(n)`) or closed-form functions. No external audio is used.
- **V2.1 baseline.** `tests/measure_v21.py` and `tests/baseline_v2.py` regenerate every published V2.1 number.
- **Experiment baseline.** `experiments/exp_model.py` with experiments off is bit-identical to V2.1. Every experiment result is therefore a difference against the exact baseline, not against an approximation.
- **Environment.** Intel Xeon @ 2.10 GHz, 2 vCPU cloud VM; Python 3, numpy 2.5.3, scipy 1.18.1, numba 0.68.1.
