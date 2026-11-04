# Tubby Filter 2.2.0-rc1

A stepped dub high-pass filter with console drive, for Ableton Live (Max for Live audio effect). It is inspired by the switched high-pass on King Tubby's desk, and it is a character model, not a circuit clone.

> **Release status: 2.2.0-rc1, BLOCKED pending native validation.** Every automated test passes on the shipped source when it's run through an independent GenExpr executor on Linux ([sim]). The one exception is an intentional strict expected failure, known issue KI-01. The device has **not** been compiled by gen~, loaded in Max, or run in Ableton Live. See `validation/V22_RELEASE_READINESS.md`.

| Version | Where | Status |
|---|---|---|
| **2.2.0-rc1** (this release candidate) | `src/`, `device/` | V2.1 + **Motion** |
| 2.1.0-rc1 (baseline, frozen) | `legacy/v2.1/` (SHA-256 pinned); git tag `v2.1.0-rc1` | Unchanged; `--v21` rebuilds it byte-for-byte |
| V2.2 research | `experiments/`, `research/` (branch `dev/v2.2-research`) | **Experimental.** Not the release. Superseded by rc1 where they differ. |
| V2 / V1 | `legacy/v2/`, `v1/` | Historical |

## Install
Drag `device/Tubby Filter.amxd` onto an audio track (Live 12, Max for Live). If Live rejects it, open `device/Tubby Filter.maxpat` in Max and choose **File → Save As Device…**. Windows build and setup: `docs/BUILD_WINDOWS.md`.

## Controls
These are the V2.1 controls (names, ranges, defaults and layout unchanged) **plus Motion**.

| Control | Parameter | Range (default) | What it does |
|---|---|---|---|
| **Filter** (big knob) | `Tubby Filter` | FLAT · 70 · 100 · 150 · 250 · 500 · 1k · 2k · 3k · 5k · 7.5k · 10k (FLAT) | Stepped high-pass |
| **Filter R** | `Filter R` | same (FLAT) | Right-side cutoff, used in Dual only |
| **Reso** | `Reso` | Q 0.5–8 (1.4) | Resonance |
| **Drive** | `Drive` | 0–100 % (20) | Console saturation, 0 to +18 dB; 0 % is clean |
| **Output** | `Output` | −24 to +12 dB (0) | Output level |
| **Glide** | `Glide` | 0–2000 ms (0) | How the cutoff moves between steps: 0 = hard switch |
| **Click** | `Click` | 0–100 % (30) | Switch sound on every step move, at any Glide |
| **Mix** | `Mix` | 0–100 % (100) | Dry/wet, phase-aligned internally |
| **Motion** *(new)* | `Motion` | 0–100 % (**0**) | Resonance blooms while the cutoff is **moving** and relaxes when it stops. 0 = exactly V2.1. |
| **Slope** | `Slope` | 12 / 18 dB (18) | — |
| **Stereo** | `Stereo` | Link / Dual / Mono (Link) | Click-free switching |
| **Drive Cal** | `Drive Cal` | Peak / Unity (Unity) | Drive gain calibration |
| **Mode** | `Mode` | Filter / Drive (Filter) | Drive = filter bypassed |

### Motion
- **What drives it:** Motion responds to *how fast the cutoff is moving*, not where it is. It measures the cutoff's speed in octaves per second and maps it to an amount from 0 to 1 (8 oct/s gives half). That amount passes through an envelope with a 2 ms attack and a 120 ms release.
- **What it does:** it multiplies the filter's Q by up to 1 + 4 × Motion.
- **What it doesn't do:** the cutoff's path is never changed (tested bit-exact). With a still cutoff, any Motion setting sounds exactly like Motion 0 (tested bit-exact).

**How it behaves** ([sim], 48 kHz):
- **Slow glides** (2 s) are barely affected: +0.3 dB.
- **Medium and fast glides** (300–50 ms) bloom by +4 to +6 dB.
- **Hard steps** give a short bloom of about +3.7 dB (20 ms loudness), which decays by about 20 dB within 0.3–0.4 s.

**Known issues** in `validation/V22_KNOWN_ISSUES.md`:
- **KI-01:** a faint transient on hard steps at high Motion.
- **KI-04:** tones that sit on a fast-moving resonance can get noticeably louder.

## Repository

```
src/          tubby_filter.genexpr      V2.2 DSP: the single source of truth
              build_device.py           deterministic build (default 2.2.0-rc1; --v21; --candidate)
device/       Tubby Filter.amxd / .maxpat, build_manifest.json
legacy/v2.1/  frozen V2.1 source and device + SHA256
tools/        gsx.py (GenExpr executor, NOT gen~), gen_compat.py (static gen~ audit), halfband.py
tests/        test_v22.py (V2.2 suite), test_regression.py (V2.1 behaviour suite, runs on V2.2
              and, with TUBBY_TARGET=v2.1, on V2.1), model_v22.py / model_v21.py (reference models)
validation/   V22_RELEASE_READINESS.md, V22_TEST_RESULTS.md, V22_COMPARISON_REPORT.md,
              V22_MOTION_VALIDATION.md, V22_LATENCY_PHASE.md, V22_KNOWN_ISSUES.md,
              ABLETON_LIVE_12_QA.md, capture kit (make_signals.py, cases.py, compare_capture.py),
              null_test.py, v22_report.py
reports/v22/  measurements JSON, plots, generated audio (reference, demos, KI-01 comparisons)
docs/         DSP_ARCHITECTURE.md, BUILD_WINDOWS.md, CHANGELOG.md, TEST_METHODOLOGY.md
experiments/, research/   V2.2 research material (EXPERIMENTAL, kept for reference)
```

## Build and test
The build needs only Python 3.10+. The tests also need `numpy scipy numba matplotlib pytest`.

```
python3 src/build_device.py                          # device/ (2.2.0-rc1)
python3 -m pytest -q tests experiments               # full automated suite (about 2.5 min)
TUBBY_TARGET=v2.1 python3 -m pytest -q tests/test_regression.py   # same suite on frozen V2.1
python3 validation/v22_report.py                     # reports/v22 (measurements, plots, audio)
python3 validation/make_signals.py 44100 48000 96000 # Live capture material
```

**Result labels used throughout:**
- **[sim]**: the shipped source executed by GSX on Linux.
- **[ref-model]**: research model.
- **BLOCKED**: needs Max or Live.
- **NOT TESTED**: not attempted.

No result in this repository comes from native gen~ or Ableton Live, and no audio was listened to.
