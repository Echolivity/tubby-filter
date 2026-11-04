# Latency and phase — 2.2.0-rc1

**Environment:** [sim], the shipped source executed by GSX on Linux. **Plugin Delay Compensation (PDC) in Ableton Live is BLOCKED:** Live isn't available here. The manual procedure is items PAR-1/2 and L-PDC-1/2 in `ABLETON_LIVE_12_QA.md`.

## 1. Where the latency comes from
- **No buffers or lookahead.** The only delay is the 2× polyphase IIR half-band oversampler, which runs only when the host rate is below 60 kHz.
- **Motion doesn't change latency.** With FLAT and Drive 0, the impulse response at Motion 0 and Motion 100 is bit-identical to V2.1 at all five rates (`test_L01`).

## 2. Measured group delay (FLAT, Drive 0), in host samples

| Rate | 20 Hz | 100 Hz | 1 kHz | 5 kHz | 10 kHz | 15 kHz | 18 kHz | Impulse peak |
|---|---|---|---|---|---|---|---|---|
| 44.1 kHz | 3.067 | 3.067 | 3.076 | 3.288 | 4.109 | 6.395 | 10.208 | sample 4 |
| 48 kHz | 3.067 | 3.067 | 3.074 | 3.252 | 3.916 | 5.581 | 7.889 | sample 4 |
| 88.2 / 96 / 192 kHz | 0 | 0 | 0 | 0 | 0 | 0 | 0 | sample 0 |

The group delay is **frequency-dependent** (the IIR has non-linear phase): 3.07 samples, about 0.07 ms at 44.1 kHz, up to about 5 kHz, then rising.

## 3. Internal dry/wet alignment
Mix blends dry and wet *inside* the oversampled domain, so both paths carry the same phase. With FLAT and Drive 0, Mix at 0/30/50/70 % is magnitude-flat within 0.01 dB to 20 kHz at 44.1, 48 and 96 kHz (`test_L02`). **The Mix control has no comb filtering.**

## 4. Parallel routing (external dry copy)
This is a null test of the processed signal against a dry copy delayed by *d* samples (FLAT, Drive 0), in dB, where lower is a better null:

| Rate | d | 100 Hz | 1 kHz | 3 kHz | 5 kHz | 10 kHz | 15 kHz |
|---|---|---|---|---|---|---|---|
| 44.1 kHz | 0 (current: nothing declared) | −27.2 | **−7.3** | +1.8 | +5.1 | +2.5 | +4.9 |
| 44.1 kHz | 3 (proposed declaration) | −60.4 | **−40.0** | −28.0 | −20.1 | −5.3 | +4.5 |
| 48 kHz | 0 | −28.0 | −8.0 | +1.1 | +4.6 | +4.3 | +0.4 |
| 48 kHz | 3 | −61.1 | −40.8 | −29.2 | −21.5 | −7.4 | +2.7 |
| 96 kHz | 0 | perfect | perfect | perfect | perfect | perfect | perfect |
| 96 kHz | 3 | −34.2 | −14.2 | −4.7 | −0.5 | +4.4 | +6.0 |

Best integer delay per band at 44.1 kHz:

| Band | Best delay | Residual |
|---|---|---|
| 20–500 Hz | **3** | −50.9 dB |
| 500–2000 Hz | **3** | −37.1 dB |
| 2–8 kHz | **3** | −16.9 dB |
| 8–18 kHz | **4** | −2.9 dB |

## 5. Is the proposed 3-sample declaration mathematically justified?
**Partly.**
- **For it:** 3 is the correct integer for the band below 8 kHz at 44.1/48 kHz. The true low-frequency group delay is 3.067 samples, so rounding to 3 leaves an error of 0.067 samples. Declaring it would improve a parallel null at 1 kHz from −7 to −40 dB.
- **Against it:**
  - **No integer is right for the whole band.** The group delay rises to 10 samples at 18 kHz, so an IIR oversampler can't null completely at high frequencies with any declared value.
  - **The latency depends on the sample rate.** It's 3 samples below 60 kHz and 0 above, so a fixed declaration of 3 would *create* a 3-sample error at 88.2 kHz and up (96 kHz: 1 kHz null −14 dB against perfect today). That can only be avoided with an extra constant 3-sample delay at ≥ 60 kHz (research experiment X7), which adds latency at high rates.
  - **Whether Live honours a Max for Live *Defined Latency* for this device hasn't been verified.**

**Decision for rc1: no latency declared.** That avoids hard-coding compensation from simulated results. The QA procedure L-PDC-2 measures the declared-latency variant in Live, and the decision follows that measurement (KI-03).

## 6. Aliasing and oversampling behaviour (unchanged from V2.1)
- Stopband about −99 dB; passband flat within 0.0001 dB to 20 kHz.
- Aliasing on a 7 kHz tone at −6 dBFS with Drive 50: −81 dB at 44.1 kHz and −88 dB at 48/96 kHz. Motion doesn't touch the oversampler or the drive. Motion 0 is bit-identical to V2.1, and a static cutoff is bit-identical at any Motion setting.

**Plot:** `reports/v22/img/latency_phase.png` (group delay; null with d = 0 and d = 3).
