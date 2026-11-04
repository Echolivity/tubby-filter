# Tubby Filter 2.1

A stepped dub high-pass filter with console drive, for Ableton Live (Max for Live audio effect). It is inspired by the switched high-pass on King Tubby's mixing desk. It is a character model, not a circuit clone.

> **Release status: candidate, not certified.** Every automated test passes on the shipped source, run through an independent executor. The device has **not** yet been run in Max or Ableton Live. See `docs/RELEASE_CHECKLIST.md` and `validation/LIVE_VALIDATION.md`.

## Install
Drag `device/Tubby Filter.amxd` onto an audio track. If Live rejects it, open `device/Tubby Filter.maxpat` in Max and choose **File → Save As Device…**.

## Controls
The controls are the same as in V2. The only behaviour change you'll notice is Click (see below).

| Control | What it does |
|---|---|
| **Filter** (big knob) | Stepped high-pass: FLAT · 70 · 100 · 150 · 250 · 500 · 1k · 2k · 3k · 5k · 7.5k · 10k Hz. |
| **Filter R** | Right-side cutoff; only active in Stereo = Dual. |
| **Reso** | Resonance, Q 0.5–8. |
| **Drive** | Console saturation, 0 to +18 dB into the shaper. 0 % is clean. |
| **Output** | −24 to +12 dB. |
| **Glide** | How the filter frequency moves between steps. 0 = hard switch; higher values glide over that many ms. |
| **Click** | Level of the switch "clunk". It sounds on **every** step move, whatever the Glide setting. Set it to 0 for silent moves. |
| **Mix** | Dry/wet. |
| **Slope** | 12 or 18 dB/oct. |
| **Stereo** | **Link**: both sides identical. **Dual**: Filter R sets the right side. **Mono**: sums L+R first. Switching between modes is click-free. |
| **Drive Cal** | **Unity**: quiet material keeps its level. **Peak**: full-scale stays full-scale. Switching is click-free. |
| **Mode** | **Drive**: filter bypassed, drive only. |

At 44.1 and 48 kHz the drive and filter run 2× oversampled, so the filter's top steps and the drive's aliasing behave the same as at 88.2/96 kHz. This adds about 0.07 ms of delay, which is not reported to Live.

## Repository

```
src/        tubby_filter.genexpr   the DSP (single source of truth)
            build_device.py        deterministic build -> device/
device/     Tubby Filter.amxd / .maxpat, build_manifest.json (SHA-256)
tools/      gsx.py                 runs the GenExpr source (for testing; not gen~)
            halfband.py            oversampler filter design
tests/      test_regression.py     90 automated tests (pytest)
            model_v21.py           independent reference model
            measure_v21.py         full measurement report -> reports/
            baseline_v2.py         V2 "before" measurements -> reports/
            metrics.py             shared analysis
validation/ LIVE_VALIDATION.md     Live test procedure and checklist (not yet performed)
            make_signals.py, cases.py, compare_capture.py   capture kit: Live renders vs reference
reports/    MEASUREMENTS_V21.md, *.json, img/
docs/       DSP_ARCHITECTURE.md, TEST_METHODOLOGY.md, CHANGELOG.md, RELEASE_CHECKLIST.md
legacy/v2/  untouched V2 source (hash-pinned), V2 docs and scripts
```

## Build and test
Requires Python 3.10+ with `numpy scipy numba matplotlib pytest`.

```
python3 src/build_device.py               # rebuild device/ (byte-identical for the same source)
python3 -m pytest -q tests                # 90 tests, about 1 minute
python3 tests/measure_v21.py              # regenerate reports/ (about 90 s)
python3 validation/make_signals.py 48000  # capture-kit signals for Live testing
```

Edit only `src/tubby_filter.genexpr`, then rebuild. A test fails if the shipped device doesn't match a fresh build.
