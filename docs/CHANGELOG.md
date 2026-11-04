# Changelog

## 2.1.0 — DSP stabilisation and validation release

The sound and workflow are unchanged. No controls were added or removed, and no parameter changed meaning. Each entry gives its evidence; **[sim]** means the shipped source was executed by GSX (see TEST_METHODOLOGY.md). Nothing here has been verified in gen~ or Live yet.

### DSP (`src/tubby_filter.genexpr`)
1. **Stereo-mode changes are click-free.**
   - Mono uses a 10 ms input crossfade. The Link↔Dual change moves the right channel's frequency over 20 ms in the log domain, and its FLAT weight is crossfaded too.
   - Link→Mono artefact: −24.0 → −76.6 dBFS **[sim]**.
2. **Drive Cal (Unity/Peak) changes are click-free** with a 20 ms divisor crossfade. Artefact: −11.8 → −71.3 dBFS **[sim]**.
3. **Mode (Filter/Drive) has its own 10 ms crossfade.** In V2 the bypass followed the Glide time, so with long glides, Drive mode took up to 2 s to engage. Artefact: −63.4 → −71.2 dBFS.
4. **Click/Glide rule redefined and made consistent.**
   - Click now fires on every step move at any Glide setting. V2 muted it whenever Glide > 0.
   - It never fires on stereo-mode changes. V2 clicked when Link→Dual changed the right cutoff.
   - In Dual, Filter R clicks only the right channel.
   - See DSP_ARCHITECTURE §6.
5. **2× oversampling below 60 kHz** (polyphase IIR half-band, 8 coefficients, −99 dB stopband) for drive and filter.
   - Frequency-response error at 44.1 kHz: 4.48 → 1.01 dB.
   - Aliasing at 44.1 kHz for 7 kHz at Drive 50: −34 → −81 dB.
   - Both **[sim]**.
6. **Explicit-state kernels** were needed to run the DSP twice per sample. The filter and drive maths are unchanged: at ≥ 88.2 kHz V2.1 equals V2 within 10⁻¹² **[sim]**.
7. **Mix dry path taken inside the oversampled domain**, so the dry and wet signals stay phase-aligned.
8. **Reset on sample-rate change and device re-activation.**
   - All DSP state is zeroed and crossfades jump to their targets.
   - The output ramps from the dry input to the processed signal over 10 ms.
   - The new internal `active` parameter is fed by the middle outlet of `live.thisdevice`.
9. **Start-up**: the output gain starts at its target instead of fading in from 0. The 10 ms dry→processed ramp now covers start-up.
10. **Init constant**: the frequency state starts at the exact `log(20)`; V2 used `2.9957` (output difference up to 3.3·10⁻⁶).
11. **Mono is bit-exact**: L = R after the start-up ramp. V2 was also bit-exact, but a crossfade added in development broke it; this was caught by a test and fixed.
12. **Click mute** now also covers sample-rate changes and re-activation, not only load.

### Device (`src/build_device.py`)
- `live.thisdevice` middle outlet → `prepend active` → gen~.
- The build is deterministic and writes `device/build_manifest.json` with SHA-256 hashes. Two builds from the same source give byte-identical files, and a test checks the shipped .amxd against a fresh build.
- Version 2.1.0 is shown on the panel and in the device description. The layout and controls are unchanged.

### Tooling and tests
- `tools/gsx.py`: runs the shipped GenExpr source, with a History read-after-write lint.
- `tools/halfband.py`: half-band design (HIIR elliptic method).
- `tests/model_v21.py`: independent reference model, bit-exact against the source.
- `tests/test_regression.py`: 90 automated tests. `tests/baseline_v2.py` and `tests/measure_v21.py`: measurement reports.
- `validation/`: Live capture kit (signal generator, case list, comparison tool with self-test) and the Live validation checklist.

### Repository
- `legacy/v2/` holds the untouched V2 source (SHA-256 pinned and checked by a test), plus V2's docs, model and measurement script.
- Git history: `v2.0` baseline → GSX → V2.1 DSP → validation and fixes → docs.

### Fixed during V2.1 development (caught by tests before release)
- A measurement bug that joined L and R before filtering, which created a fake −64 dB artefact.
- The capture comparison only checked latency in one case; it now checks it in every case.

## 2.0.0
See `legacy/v2/docs/CHANGES.md`.
