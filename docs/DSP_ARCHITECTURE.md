# DSP architecture

All DSP lives in one gen~ codebox (`src/tubby_filter.genexpr`), compiled by Max to native code. The device has no lookahead, no buffers and no oversampling, so its **latency is 0 samples**.

```
in L ─┐              ┌─ drive ─ HP 2-pole ─┬─ 1-pole HP ─┐
      ├─ stereo mode ┤   (cal)   TPT SVF   └─────────────┴─ slope xfade ─ FLAT/IN xfade ─┐
in R ─┘ (Link/Dual/  └─ drive ─ HP 2-pole ─ … (same, own state, own cutoff in Dual)      │
         Mono)                                                                           │
                       dry ───────────────────────────────────────── Mix ─ Output ─ + switch transient
                                                                                     ─ safety knee ─ NaN guard ─ out
```

## 1. Stereo routing
- **Link**: both channels get the same step, the same smoothed cutoff and the same coefficients. Measured: identical input on L and R gives bit-identical L/R output. Each side of a stereo signal is processed exactly as a mono signal would be, so the stereo image cannot move.
- **Dual**: separate step (`knobr`), separate frequency glide and separate FLAT crossfade on the right side. All other controls are shared.
- **Mono**: `(L+R)/2` feeds both channels, so the output is bit-identical L = R.
- The filter, DC-blocker and slew states are always per channel, so switching between modes never shares state.

## 2. Console drive
The transfer function is

    s(x)  = tanh(G·x + b) − tanh(b)          G = 10^(18·d/20), b = 0.25·d, d = Drive/100

- The **bias b** makes the curve asymmetric, which produces even harmonics as well as odd ones. Subtracting `tanh(b)` keeps zero in giving zero out.
- **Unity calibration** (default) divides by the slope at the origin, `s'(0) = G·(1 − tanh²b)`. Small-signal gain is then exactly 1 (0.00 dB measured at every drive setting). Larger signals compress: the output ceiling is roughly `(1 − tanh b)/s'(0)`.
- **Peak calibration** divides by `(tanh(G+b) − tanh(b−G))/2`, the mean full-scale output. A 0 dBFS input stays within about ±2.6 dB of 0 dBFS, and low-level gain rises with drive (up to +17.5 dB).
- The bias leaves a small DC offset on loud asymmetric material. A **5 Hz one-pole DC blocker** removes it. This matters in FLAT and Drive-only mode, where the high-pass is not doing that job.
- **Drive 0 is a clean path**: the shaper is faded in over the first 12.5 % of the Drive range (`amt = clamp(8d, 0, 1)`), so 0 % gives a bit-exact dry signal.
- **Aliasing**: there is no oversampling. tanh with up to +18 dB pre-gain aliases audibly on bright, hot material at 44.1/48 kHz. This is a deliberate trade for zero latency and low CPU. Oversampling in M4L means `poly~ @resampling`, which adds latency and uses Max's fixed resampling filters, so it was not added.

## 3. Filter
- **Topology**: a 2-pole TPT (topology-preserving transform, zero-delay feedback) state-variable filter, high-pass output, Zavalishin form. For the 18 dB slope a TPT one-pole high-pass is added at the same cutoff. The slope switch crossfades between the two outputs over a 10 ms time constant, so changing slope never clicks.
- **Why this topology was kept**: the coefficients are a closed-form function of cutoff and Q, it is unconditionally stable for any `k = 1/Q > 0` and any cutoff (including while the cutoff is being modulated per sample), and it is cheap. The alternatives were biquad direct forms, which have state-dependent transients and can blow up under fast coefficient changes, and a ladder, which is a low-pass structure and needs more CPU for a high-pass. Neither is an improvement for a switched high-pass.
- **Cutoff mapping**: `g = tan(π·fc/sr)` (bilinear prewarp). This is exact at fc at any sample rate.
- **Measured limitation**: bilinear frequency warping makes the 5k/7.5k/10k steps slightly sharper at 44.1/48 kHz than an ideal analog filter. The worst case at the resonant peak or above is 2.9 dB, and up to 4.5 dB deeper in the skirt at −20 dB. Steps up to 3 kHz stay within 0.4 dB. Adjusting the damping does not fix this, because it comes from warping of the frequency axis itself. This was tested and documented rather than patched.
- **Steps**: FLAT plus 70, 100, 150, 250, 500, 1k, 2k, 3k, 5k, 7.5k and 10k Hz, unchanged from v1. Spacing is dense where dub mixing works (bass and kick region) and wide at the top. FLAT parks the cutoff at 20 Hz and crossfades to the dry path.

## 4. Switching and glide
- The frequency moves in the **log domain** through a one-pole slew. With Glide = 0 its time constant is a fixed **0.5 ms** floor, which keeps the step abrupt and identical at every sample rate. In v1 the jump took exactly one sample, so its sharpness depended on the sample rate.
- **FLAT ↔ filter** crossfades over `max(4 ms, Glide)`.
- In the passband, step changes cause no level jumps: passband gain at 20 kHz is 0.00 dB for every step from 70 Hz to 7.5 kHz (Q 0.707).

## 5. Switch transient (design choice, not a measurement of any real switch)
- **Source**: uniform noise, scaled by `√(sr/44100)` so its in-band density is independent of sample rate, then band-limited 500 Hz–5 kHz with two one-pole filters whose cutoffs are set in Hz.
- **Envelope**: three decaying bursts at 0, 1.1 and 2.6 ms, with amplitudes 1, 0.45 and 0.20 and τ = 0.7 ms. This imitates contact bounce. All times are in seconds, so the envelope is the same at every rate.
- Each channel's transient fires only when that channel's step changes. In Link mode both fire together with the same noise, so the click stays centred.
- The transient is muted when Glide > 0, in Drive mode, and for the first 200 ms after load.

## 6. Output stage and protection
- Mix, then Output gain (one-pole smoothed, 20 ms), then the transient, then a **safety knee**. The knee is bit-transparent below +6 dBFS and soft-clips towards a +8 dBFS ceiling. It is only there to catch runaway resonance combined with drive and +12 dB output. Normal programme never reaches it.
- **NaN/Inf**: every recursive state passes through `fixnan(fixdenorm())`, and so does each output. Injecting NaN or Inf at the input yields 0 for those samples, after which the filter recovers. This was tested.
- **Denormals**: `fixdenorm` on every state. After an impulse, 5 s of silence decays below −400 dBFS with no subnormal values in the output.

## 7. Parameter smoothing and persistence
- Reso, Drive and Mix are smoothed over 20 ms, Slope over 10 ms, and Output over 20 ms (45 ms from 10 % to 90 %, measured at all four rates). Mode and Stereo switch instantly, because their effect is already crossfaded.
- `live.thisdevice` re-sends every control's value into gen~ when the device loads, so a restored set always reaches the DSP. Parameter values are saved by Live.
- **Compatibility**: the v1 parameter long names and ranges are kept: *Tubby Filter*, *Reso*, *Drive*, *Glide*, *Click*, *Mix*, *Slope*. *Tubby Filter* is still a 12-item enum, now drawn as a big stepped dial instead of a menu.
