# Building and testing Tubby Filter 2.2.0-rc1 on Windows

**Status: these steps were not run on Windows.** They were written for Windows and run on Linux (Ubuntu 24.04, Python 3.13), using the same commands with `python3` in place of `py`. The build script uses only the Python standard library (`hashlib`, `json`, `os`, `struct`, `sys`) and has no platform-specific code.

## 1. Prerequisites
- **Python 3.10 or newer** from python.org. During setup, tick *Add python.exe to PATH*. Check it with `py --version`.
- Only for running the tests: `py -m pip install numpy scipy numba matplotlib pytest`.
- Max is **not** needed to build. Ableton Live 12 (Suite, or Standard with Max for Live) is needed to *use* and validate the device.

## 2. Build the device
Open *Command Prompt* or *PowerShell* in the extracted project folder:

```
py src\build_device.py
```

Expected output, with exactly this hash for an unmodified source:

```
built 2.2.0-rc1: 38 boxes, 45 lines, 47460 bytes, amxd sha256 76feee2fe4c2f316
```

This writes `device\Tubby Filter.amxd`, `device\Tubby Filter.maxpat` and `device\build_manifest.json`. The build is deterministic, so the same source always gives byte-identical files.

To verify, check that `certutil -hashfile "device\Tubby Filter.amxd" SHA256` matches `device\build_manifest.json`.

Other builds:

| Command | Builds |
|---|---|
| `py src\build_device.py out\v21 --v21` | The V2.1 device from `legacy\v2.1`, byte-identical to the shipped V2.1 |
| `py src\build_device.py out\cand --candidate experiments\candidate\tubby_filter_v22_candidate.genexpr` | The research candidate (labelled EXPERIMENTAL) |

**Line endings.** The source text is embedded in the device. If Git for Windows converts `src\tubby_filter.genexpr` to CRLF, the device hash changes, though the DSP doesn't. Use the ZIP as delivered, or set `git config core.autocrlf false` before cloning, to reproduce the exact hash.

## 3. Install into Live
1. Copy `device\Tubby Filter.amxd` to `Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect\`, or drag it from Explorer onto an audio track.
2. If Live reports an error, open `device\Tubby Filter.maxpat` in Max (*File → Open*), then use *File → Save As Device…* to write a new .amxd.
3. In either case, check the Max Console for `gen~` errors. Do this first; it is check **L1** in `validation/ABLETON_LIVE_12_QA.md`.

## 4. Run the automated tests (optional)

```
py -m pytest -q tests experiments
set TUBBY_TARGET=v2.1 && py -m pytest -q tests\test_regression.py
```

The second command runs the same V2.1 behaviour suite against the frozen V2.1 baseline. Numba compiles on first use, so the first test takes about 30 s.

## 5. Generate the Live capture material

```
py validation\make_signals.py 44100 48000 96000
```

Then follow `validation/ABLETON_LIVE_12_QA.md`, Part A.
