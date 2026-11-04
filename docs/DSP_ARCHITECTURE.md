# Tubby Filter 2.2.0-rc1 — DSP architecture

The source of truth is `src/tubby_filter.genexpr`, a single gen~ codebox embedded in the device by `src/build_device.py`. Every statement below describes that file.

**2.2 = 2.1 + Motion (§11).** With Motion at 0, the output is bit-identical to 2.1 at every tested rate ([sim], `tests/test_v22.py` R01–R11). §1–§10 therefore describe both versions. The 2.1 source is frozen in `legacy/v2.1/`.

The numbers marked **[sim]** come from the shipped source run through GSX, not through gen~ (see `TEST_METHODOLOGY.md`).

## 1. Signal flow

```
in1,in2 ─► stereo routing ─┬─► (host < 60 kHz) 2× up ─► CHAN ─► CHAN ─► 2× down ─┐
 (Link / Dual / Mono,      │                          (two sub-samples)          ├─► × Output ─► post-reset ─► + switch ─► safety ─► out1,out2
  10 ms crossfade)         └─► (host ≥ 60 kHz) ───────► CHAN ────────────────────┘    gain (20 ms) dry ramp   transient  knee
                                                                                                    (10 ms)

CHAN (per channel, per sample at the internal rate):
  x ─► drive: tanh(G·x+b) − tanh(b), ÷ Unity or Peak divisor (20 ms crossfade) ─► 5 Hz DC block ─► fade-in by drive amount
    ─► 2-pole TPT SVF high-pass ─► (+ 1-pole TPT HP, slope crossfade) ─► FLAT/bypass crossfade ─► Mix with x
```

The dry signal for **Mix** is taken inside the oversampled domain, so dry and wet pass through the same half-band filters and stay phase-aligned at any Mix setting.

## 2. Parameters

| Control (panel) | gen~ Param | Range | Behaviour |
|---|---|---|---|
| Filter | `knob` | 0–11 | Step index: FLAT, 70, 100, 150, 250, 500, 1k, 2k, 3k, 5k, 7.5k, 10k Hz. Rounded to the nearest step. |
| Filter R | `knobr` | 0–11 | Right-channel step; only active in Dual. |
| Reso | `reso` | 0.5–8 | Q of the 2-pole section. 20 ms smoothing. |
| Drive | `drive` | 0–100 % | Pre-gain 0 to +18 dB. 20 ms smoothing. |
| Output | `outdb` | −24 to +12 dB | 20 ms smoothing. |
| Glide | `glide` | 0–2000 ms | Time constant of the filter-frequency glide (log domain). Minimum 0.5 ms. |
| Click | `click` | 0–100 % | Level of the switch transient. |
| Mix | `blend` | 0–100 % | Dry/wet. 20 ms smoothing. |
| Slope | `slope` | 12 / 18 dB | 10 ms crossfade between the two outputs. |
| Stereo | `stereo` | Link / Dual / Mono | See §5. |
| Drive Cal | `comp` | Peak / Unity | See §4. 20 ms crossfade. |
| Mode | `drvonly` | Filter / Drive | Drive = filter bypassed. 10 ms crossfade. |
| *(internal)* | `active` | 0/1 | Device on/off state from `live.thisdevice`. Not a user control. |

All V2 parameter names, ranges and meanings are unchanged.

## 3. Filter

- **Topology** (unchanged from V2): 2-pole TPT state-variable high-pass (Zavalishin), plus a TPT 1-pole high-pass at the same cutoff for 18 dB/oct. The cutoff is set with `g = tan(π·fc/fs)`. It is stable for any Q > 0 under per-sample modulation.
- **Cause of the V2 high-frequency deviation**: the bilinear transform maps the analog frequency axis onto 0…fs/2 non-linearly. Prewarping makes the response exact *at* fc, but the shape around and below fc is compressed as fc approaches fs/2. At 44.1 kHz the 10 kHz step sits at 0.23·fs, which gave up to 4.48 dB of error in the skirt and 2.88 dB around the peak **[sim]**. Changing the damping can't correct this: it was tested in V2 and it moves the peak, not the axis.
- **Fix**: run the filter at an internal rate of at least 88.2 kHz. Below 60 kHz the drive and filter run 2× oversampled, so 44.1 behaves exactly like 88.2, and 48 like 96. Worst deviation from the analog prototype at every supported rate is now ≤ 1.01 dB **[sim]**. The remaining error is on the 10 kHz step only; steps up to 3 kHz are within 0.1 dB. Nothing is tuned for one rate: 88.2, 96, 176.4 and 192 kHz run the same code natively.

## 4. Drive

```
s(x)  = tanh(G·x + b) − tanh(b)        G = 10^(18·d/20),  b = 0.25·d,  d = Drive/100
Unity:  y = s(x) / [G·(1 − tanh²b)]                    small-signal gain exactly 1
Peak:   y = s(x) / [(tanh(G+b) − tanh(b−G)) / 2]       full scale in ≈ full scale out
```

- Changing Drive Cal crossfades between the two divisors over 20 ms. When settled, the crossfade snaps exactly to 0 or 1, so the path is bit-identical to V2.
- `amt = clamp(8d, 0, 1)` fades the shaper in over the first 12.5 % of the Drive range, so Drive 0 is a clean path.
- A 5 Hz DC blocker removes the offset the bias creates.
- **Aliasing**: measured **[sim]** at 44.1 kHz with a −6 dBFS tone at Drive 50 %. The 7 kHz tone went from −34 dB (V2) to −81 dB (V2.1) and the 11 kHz tone from −19 dB to −53 dB, counting only energy below 20 kHz. Aliasing at 96 kHz host rate is unchanged, because no oversampling runs there; it already had the benefit of the higher rate.
- **Character**: harmonics 2–7 of a 100 Hz tone at 48 kHz match V2 within **0.001 dB [sim]**. The drive curve itself was not changed.

## 5. Stereo

- **Link**: both channels use the left step. When settled, the right channel's frequency and weight are copied from the left, so identical input gives bit-identical output.
- **Dual**: the right channel uses Filter R. Switching between Link and Dual moves the right channel's target frequency through a 20 ms log-domain crossfade, then through the normal glide.
- **Mono**: (L+R)/2 feeds both channels through a 10 ms crossfade. When settled, both sides use exactly the same input, so L = R bit for bit.
- There is no crosstalk in Link or Dual: an input only on L gives exactly 0 on R **[sim]**.

## 6. Click / Glide interaction (defined precisely)

- The **switch transient fires once per step change of a step control**, on the channel that control drives:
  - Filter: left channel, and right channel in Link and Mono.
  - Filter R: right channel, in Dual only.
- **Glide has no effect on the transient.** Glide sets how the filter *frequency* moves; Click is the sound of the switch itself. Both happen independently, at any Glide value. For a silent glide, set Click to 0.
- **It never fires on**: stereo-mode changes (including Link→Dual moving the right cutoff), device load, sample-rate change, re-activation, Filter R moves in Link or Mono, or Drive mode.
- **Rapid stepping**: each new step restarts the burst envelope, so bursts never stack. Stepping every 2 ms peaks within 1.6× of a single step **[sim]**.
- **Sound**: band-limited noise (500 Hz–5 kHz), three decaying bursts at 0, 1.1 and 2.6 ms. Level and spectrum are independent of sample rate.
- **Change from V2**: V2 silenced Click whenever Glide > 0, which contradicted V2's own manual in places and made Click unusable with Glide. V2.1 follows the rule above.

## 7. Discrete-control transitions

| Control | Mechanism | Worst artefact **[sim]**, 100 Hz at −12 dBFS, content > 3 kHz |
|---|---|---|
| Stereo Link→Mono | 10 ms input crossfade | −76.6 dBFS (V2: −24.0) |
| Stereo Link↔Dual | 20 ms right-frequency crossfade | −112 to −128 dBFS (V2: −63 to −83) |
| Drive Cal Unity↔Peak | 20 ms divisor crossfade | −71.3 dBFS (V2: −11.8) |
| Mode Filter→Drive | 10 ms bypass crossfade | −71.2 dBFS (V2: −63.4) |
| Slope | 10 ms crossfade (unchanged) | −111.5 dBFS |
| Filter step, Click 0 | 0.5 ms log glide floor (unchanged) | −64.8 dBFS. This is the **intended hard-switch character**, kept from V2. |

## 8. Oversampling

- **Filter**: polyphase IIR half-band, two branches of 4 first-order allpass sections each (8 coefficients, transition 0.04), designed by `tools/halfband.py`. The coefficients are embedded in the source and checked by the tests.
- **Response [sim]**: stopband −99 dB; passband flat within 0.0001 dB to 20 kHz at 44.1 and 48 kHz.
- **Cost**: the half-band filters have a non-linear phase. Measured group delay at 44.1 kHz is **3.1 samples at 1 kHz** (0.07 ms), 4.1 at 10 kHz and 10.2 at 18 kHz. The device does not report this to Live; see Known limitations.
- **Why 2× and only below 60 kHz**: 2× brings the internal rate to 88.2/96 kHz, which fixes the filter warping and cuts audible aliasing by 30–70 dB for typical settings. Higher factors would cost more CPU for gains only at extreme drive on very high tones. At 88.2 kHz and above the host rate is already high enough, so oversampling there would add CPU without solving a measured problem.

## 9. State, resets and numerical safety

- **Explicit-state kernels**: each History is read at the start of a frame and written once. The GSX lint rejects any read-after-write, so the code doesn't depend on unspecified gen~ semantics.
- **Every state write** passes `fixnan(fixdenorm())`. NaN or Inf at the input yields 0 for those samples and the filter recovers. A silence tail decays with no subnormal values **[sim]**.
- **Reset** happens on the first frame, on a sample-rate change, and when `active` goes 0→1. All filter, half-band and DC states are zeroed, and the crossfade weights jump to their targets. The output then crossfades from the unprocessed input to the processed signal over 10 ms. The switch transient is muted for 200 ms.
- **Safety knee**: bit-transparent below +6 dBFS, with a soft ceiling at +8 dBFS. Every extreme or random-automation run peaked at ≤ +8.0 dBFS **[sim]**.
- **Transport**: the device has no transport dependency. It keeps processing when the transport stops, as an analog unit would, so a resonant tail rings out naturally.

## 10. Known limitations

1. **Unreported latency at 44.1/48 kHz**: there are about 3 samples of group delay in the oversampler (frequency-dependent, 0.07 ms at 1 kHz). Live's delay compensation is not told about it. In a parallel setup where the device is summed with an uncompensated copy, expect slight cancellation above roughly 10 kHz. Reporting a fixed latency would not make a non-linear-phase filter phase-coherent.
2. **Aliasing is reduced, not removed**: at Drive 100 % on a 15 kHz tone at −6 dBFS it is still about −18 dB at 44.1 kHz and −25 dB at 48/96 kHz **[sim]**. Real material rarely has full-scale content there, but extreme drive on bright sources will alias.
3. **Top step accuracy**: the 10 kHz step deviates from the analog prototype by up to 1.0 dB in the skirt at 44.1/88.2 kHz, and 0.85 dB at 48/96 kHz.
4. **Unity calibration compresses loud material** at high drive (by design). Use Output to make up level.
5. **Rate-change hand-over**: when the sample rate changes, the restart produces one sample step of up to about 2× normal signal motion. Live interrupts the audio stream at that moment anyway.
6. **Not yet verified in gen~ or Live.** Whether gen~ compiles this source, and how it behaves in Live, has not been tested (see `validation/ABLETON_LIVE_12_QA.md`).
7. **Motion (2.2):** see `validation/V22_KNOWN_ISSUES.md`, KI-01 (a faint transient on hard steps) and KI-04 (a tone sitting on a fast-moving resonance gets louder).

## 11. Motion (new in 2.2)

```
per host sample, per channel:
  v   = (log-cutoff now − log-cutoff previous sample) · sr / ln 2      cutoff speed, oct/s (0 on reset)
        right channel uses the left speed while a Link↔Dual crossfade runs (not a gesture)
  m   = |v| / (|v| + 8)                                                0..1; 8 oct/s = 0.5
  env = one-pole towards m: 2 ms when rising, 120 ms when falling
  amt = Motion% / 100, smoothed 20 ms
  k   = (1 / Q) / (1 + 4 · amt · env)                                  damping; Q × up to 5
```

- **The cutoff path is untouched.** `g = tan(π·fc/fs)` comes from the same glide state as in 2.1. Motion only scales the damping `k`. Tested by exposing the internal log-cutoff trajectory: it is bit-identical at Motion 0 and 100 (`test_M12`).
- **At a stationary cutoff, v = 0 exactly,** so env stays 0, the factor is exactly 1.0, and the output is bit-identical to Motion 0 (`test_M11`, Live capture case C13).
- **Order fixed in rc1.** The speed is mapped to 0..1 *before* the envelope. The research candidate enveloped raw speed. A hard step moves at about 2000 oct/s through the 0.5 ms glide floor, so the candidate held the bloom at full strength for about 0.6 s, instead of the documented 120 ms release (KI FX-01).
- **Cost:** about 20 operations and 3 `exp` calls per host sample (the two envelope coefficients and the amount smoother).
- **Measured behaviour [sim]:** see `validation/V22_MOTION_VALIDATION.md`. Limitations: KI-01 and KI-04.
