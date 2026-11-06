{
 "patcher": {
  "fileversion": 1,
  "appversion": {
   "major": 8,
   "minor": 6,
   "revision": 0,
   "architecture": "x64",
   "modernui": 1
  },
  "classnamespace": "box",
  "rect": [
   60,
   60,
   1200,
   520
  ],
  "openinpresentation": 1,
  "devicewidth": 424.0,
  "description": "Tubby Filter 2.2.0-rc5 \u2014 stepped dub high-pass with console drive",
  "boxes": [
   {
    "box": {
     "id": "panel",
     "maxclass": "panel",
     "numinlets": 1,
     "numoutlets": 0,
     "background": 1,
     "bgcolor": [
      0.16,
      0.2,
      0.17,
      1.0
     ],
     "rounded": 0,
     "presentation": 1,
     "presentation_rect": [
      0,
      0,
      424,
      169
     ],
     "patching_rect": [
      700,
      10,
      60,
      40
     ]
    }
   },
   {
    "box": {
     "id": "title",
     "maxclass": "live.comment",
     "text": "TUBBY FILTER",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 10.5,
     "textcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "fontface": 1,
     "presentation": 1,
     "presentation_rect": [
      8,
      4,
      120,
      14
     ],
     "patching_rect": [
      700,
      62,
      120,
      18
     ]
    }
   },
   {
    "box": {
     "id": "sub",
     "maxclass": "live.comment",
     "text": "stepped hi-pass \u00b7 console drive \u00b7 v2.2",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.0,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "fontface": 0,
     "presentation": 1,
     "presentation_rect": [
      8,
      152,
      220,
      14
     ],
     "patching_rect": [
      700,
      64,
      220,
      18
     ]
    }
   },
   {
    "box": {
     "id": "plugin",
     "maxclass": "newobj",
     "text": "plugin~",
     "numinlets": 2,
     "numoutlets": 2,
     "patching_rect": [
      30,
      330,
      60,
      22
     ],
     "outlettype": [
      "signal",
      "signal"
     ]
    }
   },
   {
    "box": {
     "id": "gen",
     "maxclass": "newobj",
     "text": "gen~ @title tubby_v2_2",
     "numinlets": 2,
     "numoutlets": 2,
     "outlettype": [
      "signal",
      "signal"
     ],
     "patching_rect": [
      30,
      380,
      220,
      22
     ],
     "patcher": {
      "fileversion": 1,
      "appversion": {
       "major": 8,
       "minor": 6,
       "revision": 0,
       "architecture": "x64",
       "modernui": 1
      },
      "classnamespace": "dsp.gen",
      "rect": [
       80,
       80,
       760,
       700
      ],
      "boxes": [
       {
        "box": {
         "id": "g-in1",
         "maxclass": "newobj",
         "text": "in 1",
         "numinlets": 0,
         "numoutlets": 1,
         "patching_rect": [
          20,
          14,
          60,
          22
         ],
         "outlettype": [
          ""
         ]
        }
       },
       {
        "box": {
         "id": "g-in2",
         "maxclass": "newobj",
         "text": "in 2",
         "numinlets": 0,
         "numoutlets": 1,
         "patching_rect": [
          640,
          14,
          60,
          22
         ],
         "outlettype": [
          ""
         ]
        }
       },
       {
        "box": {
         "id": "g-code",
         "maxclass": "codebox",
         "code": "// =====================================================================\n//  Tubby Filter v2.2.0-rc5 \u2014 gen~ codebox (in1/in2 -> out1/out2)\n//  = v2.1 + Motion (movement-dependent resonance). Motion 0 == v2.1 exactly.\n//  Release candidate: validated in simulation only; native gen~ and Ableton\n//  Live validation pending (see validation/V22_RELEASE_READINESS.md).\n//  Stepped dub high-pass with console drive, inspired by the switched\n//  high-pass on King Tubby's desk. Character model, not a circuit clone.\n//\n//  Per channel:  input -> stereo routing -> [2x up] -> DRIVE -> DC block\n//    -> HP TPT SVF (+1-pole for 18 dB) -> FLAT/bypass xfade -> MIX\n//    -> [2x down] -> OUTPUT -> + switch transient -> safety knee -> NaN guard\n//\n//  2x oversampling (polyphase IIR half-band) runs when the host rate is\n//  below 60 kHz, so the drive and filter always run at 88.2 kHz or more.\n//\n//  State rules (portable gen~ semantics, checked by tools/gsx.py):\n//   * every History is read before it is written in a frame, never after\n//   * DSP kernels are pure functions: state in, state out\n//   * every state write passes fixnan(fixdenorm())\n//  Times are in ms/Hz, so behaviour is the same at any sample rate.\n//  gen~ rule: every function definition must precede ALL statements,\n//  including Param declarations (rc1 failed to compile: \"function definitions\n//  must precede all statements\"; found in Live 12, fixed in rc2).\n//  No identifier shadows a gen operator/constant (tools/gen_compat.py; 2.2.0-rc1\n//  renamed v2.1's `f` -> `hpf` and `i` -> `idx`, which collide with gen's\n//  `f` (float) and `i` (int) operators).\n// =====================================================================\n\n\n// ---------------------------------------------------------------------\n// one-pole smoother, time constant in ms\nslew(x, ms) {\n    History y(0);\n    c = 1 - exp(-1 / (max(ms, 0.01) * 0.001 * samplerate));\n    n = fixnan(fixdenorm(y + (x - y) * c));\n    y = n;\n    return n;\n}\n\n// one-pole crossfade weight for a discrete control: 0..1, snaps exactly\n// to its target once within 1e-7 so settled paths are bit-exact, and\n// jumps straight to it on reset (load / sample-rate change / re-enable)\nxfade(target, ms, reset) {\n    History y(0);\n    c = 1 - exp(-1 / (max(ms, 0.01) * 0.001 * samplerate));\n    n = y + (target - y) * c;\n    n = (reset || abs(target - n) < 1e-7) ? target : n;\n    n = fixnan(n);\n    y = n;\n    return n;\n}\n\n// state hygiene\nfx(x) {\n    return fixnan(fixdenorm(x));\n}\n\n// first-order (in z^-2 at the high rate) allpass cascade: one half-band branch\nbr4(x, a1, a2, a3, a4, s1, s2, s3, s4) {\n    y1 = a1 * x + s1;   n1 = x - a1 * y1;\n    y2 = a2 * y1 + s2;  n2 = y1 - a2 * y2;\n    y3 = a3 * y2 + s3;  n3 = y2 - a3 * y3;\n    y4 = a4 * y3 + s4;  n4 = y3 - a4 * y4;\n    return y4, n1, n2, n3, n4;\n}\n\n// one channel, one (possibly oversampled) sample: drive -> DC -> HP -> mixes\n// returns y and the five updated states\nchan(x, G, b, tb, s0, sp, cw, amt, r5, g, k, sl, w, bl, dxp, dyp, ic1, ic2, ops) {\n    // drive (see docs: s(x) = tanh(Gx+b) - tanh(b), Unity / Peak calibration)\n    sh = tanh(G * x + b) - tb;\n    yd = cw >= 1 ? sh / s0 : (cw <= 0 ? sh / sp : mix(sh / sp, sh / s0, cw));\n    // 5 Hz DC blocker\n    dy = fx(yd - dxp + r5 * dyp);\n    d = mix(x, dy, amt);\n    // TPT state-variable high-pass (Zavalishin)\n    a1 = 1 / (1 + g * (g + k));\n    a2 = g * a1;\n    a3 = g * a2;\n    v3 = d - ic2;\n    v1 = a1 * ic1 + a2 * v3;\n    v2 = ic2 + a2 * ic1 + a3 * v3;\n    h = d - k * v1 - v2;\n    // TPT one-pole high-pass for the 18 dB slope\n    G1 = g / (1 + g);\n    v = (h - ops) * G1;\n    lp = v + ops;\n    hpf = mix(h, h - lp, sl);\n    // FLAT/bypass crossfade, then dry/wet\n    y = mix(x, mix(d, hpf, w), bl);\n    return y, yd, dy, fx(2 * v1 - ic1), fx(2 * v2 - ic2), fx(lp + v);\n}\n\n// step index -> cutoff Hz (index 0 = FLAT, parked at 20 Hz)\nstepfreq(idx) {\n    return selector(idx + 1, 20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000);\n}\n\n// switch transient: three decaying bursts (contact bounce), t in seconds\nbounce(t) {\n    tau = 0.0007;\n    e1 = exp(-t / tau);\n    e2 = t >= 0.0011 ? 0.45 * exp(-(t - 0.0011) / tau) : 0;\n    e3 = t >= 0.0026 ? 0.20 * exp(-(t - 0.0026) / tau) : 0;\n    return t < 0.02 ? e1 + e2 + e3 : 0;\n}\n\n// ---- parameters (V2 names, ranges and meanings unchanged)\nParam knob(0, min=0, max=11);      // left/linked step: 0 = FLAT, 1..11\nParam reso(1.4, min=0.5, max=8);   // Q\nParam drive(20, min=0, max=100);   // % drive (0..+18 dB into the shaper)\nParam glide(0, min=0, max=2000);   // ms of filter-frequency glide\nParam click(30, min=0, max=100);   // % switch transient\nParam slope(1, min=0, max=1);      // 0 = 12 dB/oct, 1 = 18 dB/oct\nParam blend(100, min=0, max=100);  // % dry/wet\nParam knobr(0, min=0, max=11);     // right step (Dual mode only)\nParam stereo(0, min=0, max=2);     // 0 Link, 1 Dual, 2 Mono\nParam comp(1, min=0, max=1);       // 1 Unity / 0 Peak drive calibration\nParam drvonly(0, min=0, max=1);    // 1 = filter bypassed, drive only\nParam outdb(0, min=-24, max=12);   // output level, dB\n// ---- V2.1 (internal, sent by live.thisdevice; not a user control)\nParam active(1, min=0, max=1);     // device on/off state\n// ---- V2.2\nParam motion(0, min=0, max=100);   // % resonance bloom while the cutoff moves\n\n// ---------------------------------------------------------------------\n// state (all read at the top of the frame, written once at the end)\nHistory lfL(2.995732273553991), lfR(2.995732273553991); // log Hz (log 20)\nHistory wL(0), wR(0);              // FLAT -> filter weight\nHistory pK(0), pKR(0);             // previous knob / knobr steps\nHistory tL(1), tR(1);              // s since last switch, per channel\nHistory age(0);                    // s since load / reset\nHistory ogs(1);                    // smoothed output gain\nHistory rw(0);                     // dry -> processed ramp after reset\nHistory mvL(0), mvR(0);            // motion envelopes (0..1, mapped cutoff speed)\nHistory srp(0), actp(1);           // previous sample rate / active\nHistory nl1(0), nl2(0);            // click noise filters\nHistory dxL(0), dyL(0), c1L(0), c2L(0), opL(0);   // left DSP state\nHistory dxR(0), dyR(0), c1R(0), c2R(0), opR(0);   // right DSP state\nHistory uL1(0), uL2(0), uL3(0), uL4(0), uL5(0), uL6(0), uL7(0), uL8(0);\nHistory uR1(0), uR2(0), uR3(0), uR4(0), uR5(0), uR6(0), uR7(0), uR8(0);\nHistory dL1(0), dL2(0), dL3(0), dL4(0), dL5(0), dL6(0), dL7(0), dL8(0);\nHistory dR1(0), dR2(0), dR3(0), dR4(0), dR5(0), dR6(0), dR7(0), dR8(0);\n\n// half-band coefficients: 8 coefs, transition 0.04 (tools/halfband.py)\n// branch 0 = even indices, branch 1 = odd indices; ~99 dB stopband\nA0 = 0.04063346092419326;  A1 = 0.1505051290226746;\nA2 = 0.3007570559918741;   A3 = 0.4607745049614506;\nA4 = 0.6095243148961883;   A5 = 0.7385038411188573;\nA6 = 0.8492238103920661;   A7 = 0.9497427837050002;\n\nsr = samplerate;\n\n// ---- reset on sample-rate change or device re-activation\nrst = (sr != srp) || (active > 0.5 && actp < 0.5);\nkeep = 1 - rst;\nsrp = sr;\nactp = active;\n\nos2 = sr < 60000;                  // run the DSP at 2x below 60 kHz\nfs = sr * (1 + os2);               // internal DSP rate\n\nnage = rst ? 0 : min(age + 1 / sr, 1);\nage = nage;\n\n// ---- continuous controls (unchanged from V2)\nq   = max(slew(reso, 20), 0.5);\ndd  = clamp(slew(drive, 20), 0, 100) * 0.01;\nsl  = clamp(slew(slope, 10), 0, 1);\nbl  = clamp(slew(blend, 20), 0, 100) * 0.01;\nog  = rst ? dbtoa(outdb) : fx(ogs + (dbtoa(outdb) - ogs) * (1 - exp(-1 / (20 * 0.001 * sr))));\nogs = og;\n// after a reset the output crossfades from the unprocessed input (what Live\n// passes while the device is off) to the processed signal over 10 ms\nnrw = rst ? 0 : min(rw + 1 / (0.01 * sr), 1);\nrw = nrw;\n\n// ---- discrete controls -> click-free weights (V2.1)\nmode = floor(stereo + 0.5);\ndual = mode == 1;\nmw  = xfade(mode == 2, 10, rst);         // Link/Dual -> Mono input sum\ndw  = xfade(dual, 20, rst);              // right side follows knobr\ncw  = xfade(comp > 0.5, 20, rst);        // Peak (0) <-> Unity (1)\nbw  = xfade(drvonly > 0.5, 10, rst);     // filter -> drive-only\n\n// ---- input routing\nmono = (in1 + in2) * 0.5;\nxL = mw <= 0 ? in1 : (mw >= 1 ? mono : mix(in1, mono, mw));\nxR = mw <= 0 ? in2 : (mw >= 1 ? mono : mix(in2, mono, mw));\n\n// ---- drive constants: 0..+18 dB pre-gain, bias grows with drive\nG   = dbtoa(dd * 18);\nb   = 0.25 * dd;\ntb  = tanh(b);\ns0  = G * (1 - tb * tb);                         // Unity divisor\nsp  = (tanh(G + b) - tanh(b - G)) * 0.5;         // Peak divisor\namt = clamp(dd * 8, 0, 1);                       // drive 0 = clean\nr5  = exp(-twopi * 5 / fs);\n\n// ---- step selection and frequency glide (log domain)\niL  = clamp(floor(knob + 0.5), 0, 11);\niRk = clamp(floor(knobr + 0.5), 0, 11);\nltL = log(stepfreq(iL));\nltR = dw <= 0 ? ltL : mix(ltL, log(stepfreq(iRk)), dw);\ncg  = 1 - exp(-1 / (max(glide, 0.5) * 0.001 * sr));\nnlL = keep * lfL + (ltL - keep * lfL) * cg;\nnlR = keep * lfR + (ltR - keep * lfR) * cg;\nnlL = rst ? ltL : nlL;\nnlR = rst ? ltR : nlR;\nnlR = (dw <= 0 && abs(nlR - nlL) < 1e-9) ? nlL : nlR;   // Link: bit-identical\n// ---- Motion: speed of the cutoff (octaves/s), from this frame's glide step\nvL = rst ? 0 : (nlL - lfL) * sr / log(2);\nvR = rst ? 0 : (nlR - lfR) * sr / log(2);\n// a Link<->Dual change moves the right cutoff internally (20 ms); that is not a\n// performed gesture, so during the crossfade the right side uses the left speed\nvR = (dw > 0 && dw < 1) ? vL : vR;\nlfL = nlL;\nlfR = nlR;\n// map speed to 0..1 first (8 oct/s = half effect), then envelope it\n// (2 ms attack, 120 ms release), so the release time does not depend on\n// how fast the cutoff moved (rc1 fix: the research candidate enveloped the\n// raw speed, which held a hard step's bloom for ~0.6 s instead of ~120 ms)\nvaL = abs(vL) / (abs(vL) + 8);\nvaR = abs(vR) / (abs(vR) + 8);\nc2   = 1 - exp(-1 / (2 * 0.001 * sr));\nc120 = 1 - exp(-1 / (120 * 0.001 * sr));\nnmvL = fx(mvL + (vaL - mvL) * (vaL > mvL ? c2 : c120));\nnmvR = fx(mvR + (vaR - mvR) * (vaR > mvR ? c2 : c120));\nmvL = nmvL;\nmvR = nmvR;\nmsm = slew(motion * 0.01, 20);\n// damping divisor: Q is multiplied by up to 1 + 4 * motion while moving;\n// with Motion 0 this is exactly 1, so the filter is bit-identical to v2.1\nkmL = 1 / (1 + msm * 4 * nmvL);\nkmR = 1 / (1 + msm * 4 * nmvR);\nfcL = clamp(exp(nlL), 10, fs * 0.45);\nfcR = clamp(exp(nlR), 10, fs * 0.45);\n\n// FLAT <-> filter weight follows glide (never faster than 4 ms)\ncwf = 1 - exp(-1 / (max(4, glide) * 0.001 * sr));\nonL = iL > 0;\nonR = dw <= 0 ? onL : mix(onL, iRk > 0, dw);\nnwL = keep * wL + (onL - keep * wL) * cwf;\nnwR = keep * wR + (onR - keep * wR) * cwf;\nnwR = (dw <= 0 && abs(nwR - nwL) < 1e-9) ? nwL : nwR;\nwL = nwL;\nwR = nwR;\nweL = nwL * (1 - bw);\nweR = nwR * (1 - bw);\n\n// ---- filter coefficients at the internal rate\nk  = 1 / q;\ngL = tan(pi * fcL / fs);\ngR = tan(pi * fcR / fs);\n\n// ---- load state (zeroed on reset)\nsdxL = dxL * keep; sdyL = dyL * keep; s1L = c1L * keep; s2L = c2L * keep; soL = opL * keep;\nsdxR = dxR * keep; sdyR = dyR * keep; s1R = c1R * keep; s2R = c2R * keep; soR = opR * keep;\nyL = 0;\nyR = 0;\n\nif (os2) {\n    // --- 2x up (polyphase): sub-sample 0 = branch 0, sub-sample 1 = branch 1\n    u0L, n1, n2, n3, n4 = br4(xL, A0, A2, A4, A6, uL1 * keep, uL2 * keep, uL3 * keep, uL4 * keep);\n    uL1 = fx(n1); uL2 = fx(n2); uL3 = fx(n3); uL4 = fx(n4);\n    u1L, m1, m2, m3, m4 = br4(xL, A1, A3, A5, A7, uL5 * keep, uL6 * keep, uL7 * keep, uL8 * keep);\n    uL5 = fx(m1); uL6 = fx(m2); uL7 = fx(m3); uL8 = fx(m4);\n    u0R, p1, p2, p3, p4 = br4(xR, A0, A2, A4, A6, uR1 * keep, uR2 * keep, uR3 * keep, uR4 * keep);\n    uR1 = fx(p1); uR2 = fx(p2); uR3 = fx(p3); uR4 = fx(p4);\n    u1R, r1, r2, r3, r4 = br4(xR, A1, A3, A5, A7, uR5 * keep, uR6 * keep, uR7 * keep, uR8 * keep);\n    uR5 = fx(r1); uR6 = fx(r2); uR7 = fx(r3); uR8 = fx(r4);\n\n    // --- DSP at 2x: two sub-samples per channel, state threaded through\n    v0L, sdxL, sdyL, s1L, s2L, soL = chan(u0L, G, b, tb, s0, sp, cw, amt, r5, gL, k * kmL, sl, weL, bl, sdxL, sdyL, s1L, s2L, soL);\n    v1L, sdxL, sdyL, s1L, s2L, soL = chan(u1L, G, b, tb, s0, sp, cw, amt, r5, gL, k * kmL, sl, weL, bl, sdxL, sdyL, s1L, s2L, soL);\n    v0R, sdxR, sdyR, s1R, s2R, soR = chan(u0R, G, b, tb, s0, sp, cw, amt, r5, gR, k * kmR, sl, weR, bl, sdxR, sdyR, s1R, s2R, soR);\n    v1R, sdxR, sdyR, s1R, s2R, soR = chan(u1R, G, b, tb, s0, sp, cw, amt, r5, gR, k * kmR, sl, weR, bl, sdxR, sdyR, s1R, s2R, soR);\n\n    // --- 2x down: y = (A0(v1) + A1(v0)) / 2\n    e0L, q1, q2, q3, q4 = br4(v1L, A0, A2, A4, A6, dL1 * keep, dL2 * keep, dL3 * keep, dL4 * keep);\n    dL1 = fx(q1); dL2 = fx(q2); dL3 = fx(q3); dL4 = fx(q4);\n    e1L, w1, w2, w3, w4 = br4(v0L, A1, A3, A5, A7, dL5 * keep, dL6 * keep, dL7 * keep, dL8 * keep);\n    dL5 = fx(w1); dL6 = fx(w2); dL7 = fx(w3); dL8 = fx(w4);\n    e0R, z1, z2, z3, z4 = br4(v1R, A0, A2, A4, A6, dR1 * keep, dR2 * keep, dR3 * keep, dR4 * keep);\n    dR1 = fx(z1); dR2 = fx(z2); dR3 = fx(z3); dR4 = fx(z4);\n    e1R, o1, o2, o3, o4 = br4(v0R, A1, A3, A5, A7, dR5 * keep, dR6 * keep, dR7 * keep, dR8 * keep);\n    dR5 = fx(o1); dR6 = fx(o2); dR7 = fx(o3); dR8 = fx(o4);\n    yL = (e0L + e1L) * 0.5;\n    yR = (e0R + e1R) * 0.5;\n} else {\n    yL, sdxL, sdyL, s1L, s2L, soL = chan(xL, G, b, tb, s0, sp, cw, amt, r5, gL, k * kmL, sl, weL, bl, sdxL, sdyL, s1L, s2L, soL);\n    yR, sdxR, sdyR, s1R, s2R, soR = chan(xR, G, b, tb, s0, sp, cw, amt, r5, gR, k * kmR, sl, weR, bl, sdxR, sdyR, s1R, s2R, soR);\n}\n\n// ---- store DSP state\ndxL = sdxL; dyL = sdyL; c1L = s1L; c2L = s2L; opL = soL;\ndxR = sdxR; dyR = sdyR; c1R = s1R; c2R = s2R; opR = soR;\n\n// ---- output gain, then the post-reset dry -> processed ramp\noL = yL * og;\noR = yR * og;\noL = nrw >= 1 ? oL : mix(in1, oL, nrw);\noR = nrw >= 1 ? oR : mix(in2, oR, nrw);\n\n// ---- switch transient\n// Fires when a step control actually moves: Filter on the left (and on the\n// right in Link/Mono), Filter R on the right in Dual. Independent of Glide.\n// Stereo-mode changes, sample-rate resets and loading never fire it.\nchK  = iL != pK;\nchKR = iRk != pKR;\npK = iL;\npKR = iRk;\nfireL = chK;\nfireR = dual ? chKR : chK;\nntL = (fireL && !rst) ? 0 : min(tL + 1 / sr, 1);\nntR = (fireR && !rst) ? 0 : min(tR + 1 / sr, 1);\nntL = rst ? 1 : ntL;\nntR = rst ? 1 : ntR;\ntL = ntL;\ntR = ntR;\n// band-limited noise 500 Hz..5 kHz, level normalised for sample rate\nnz = noise() * sqrt(sr / 44100);\nc5k  = 1 - exp(-twopi * 5000 / sr);\nc500 = 1 - exp(-twopi * 500 / sr);\nnn1 = fx(nl1 * keep + (nz - nl1 * keep) * c5k);\nnn2 = fx(nl2 * keep + (nn1 - nl2 * keep) * c500);\nnl1 = nn1;\nnl2 = nn2;\nnb = nn1 - nn2;\n// muted for 200 ms after load/reset and in drive-only mode\ncgn = click * 0.01 * 0.5 * (1 - bw) * (nage > 0.2);\noL = oL + nb * bounce(ntL) * cgn * og;\noR = oR + nb * bounce(ntR) * cgn * og;\n\n// ---- safety: bit-transparent below +6 dBFS, soft knee to a +8 dBFS ceiling\nth = 1.9953;\nkn = 0.5166;\naL = abs(oL);\naR = abs(oR);\noL = aL > th ? sign(oL) * (th + kn * tanh((aL - th) / kn)) : oL;\noR = aR > th ? sign(oR) * (th + kn * tanh((aR - th) / kn)) : oR;\n\nout1 = fixnan(oL);\nout2 = fixnan(oR);\n",
         "fontface": 0,
         "fontname": "<Monospaced>",
         "fontsize": 11,
         "numinlets": 2,
         "numoutlets": 2,
         "outlettype": [
          "",
          ""
         ],
         "patching_rect": [
          20,
          48,
          680,
          580
         ]
        }
       },
       {
        "box": {
         "id": "g-out1",
         "maxclass": "newobj",
         "text": "out 1",
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          20,
          645,
          60,
          22
         ]
        }
       },
       {
        "box": {
         "id": "g-out2",
         "maxclass": "newobj",
         "text": "out 2",
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          640,
          645,
          60,
          22
         ]
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "source": [
          "g-in1",
          0
         ],
         "destination": [
          "g-code",
          0
         ]
        }
       },
       {
        "patchline": {
         "source": [
          "g-in2",
          0
         ],
         "destination": [
          "g-code",
          1
         ]
        }
       },
       {
        "patchline": {
         "source": [
          "g-code",
          0
         ],
         "destination": [
          "g-out1",
          0
         ]
        }
       },
       {
        "patchline": {
         "source": [
          "g-code",
          1
         ],
         "destination": [
          "g-out2",
          0
         ]
        }
       }
      ]
     }
    }
   },
   {
    "box": {
     "id": "plugout",
     "maxclass": "newobj",
     "text": "plugout~",
     "numinlets": 2,
     "numoutlets": 0,
     "patching_rect": [
      30,
      430,
      60,
      22
     ]
    }
   },
   {
    "box": {
     "id": "thisdev",
     "maxclass": "newobj",
     "text": "live.thisdevice",
     "numinlets": 1,
     "numoutlets": 3,
     "patching_rect": [
      30,
      10,
      100,
      22
     ],
     "outlettype": [
      "bang",
      "int",
      "int"
     ]
    }
   },
   {
    "box": {
     "id": "active-p",
     "maxclass": "newobj",
     "text": "prepend active",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      150,
      40,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "step",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      10,
      24,
      96,
      118
     ],
     "patching_rect": [
      30,
      60,
      96,
      118
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 11.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 0,
       "parameter_longname": "Tubby Filter",
       "parameter_shortname": "Filter",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Tubby Filter",
       "parameter_info": "Stepped high-pass cutoff: FLAT, 70 Hz ... 10 kHz (snaps to the nearest step). Linked/Mono: both sides; Dual: left side. Can be modulated by Live's LFO.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "shownumber": 0,
     "varname": "Tubby Filter"
    }
   },
   {
    "box": {
     "id": "step-p",
     "maxclass": "newobj",
     "text": "prepend knob",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      30,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "stepr",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      110,
      44,
      52,
      62
     ],
     "patching_rect": [
      142,
      60,
      52,
      62
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 11.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 0,
       "parameter_longname": "Filter R",
       "parameter_shortname": "Filter R",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Filter R",
       "parameter_info": "Right-side cutoff (snaps to the nearest step). Active only in Dual stereo mode.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "shownumber": 0,
     "varname": "Filter R"
    }
   },
   {
    "box": {
     "id": "stepr-p",
     "maxclass": "newobj",
     "text": "prepend knobr",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      142,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "step-rnd",
     "maxclass": "newobj",
     "text": "expr int($f1+0.5)",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      506,
      120,
      110,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "step-sel",
     "maxclass": "newobj",
     "text": "sel 0 1 2 3 4 5 6 7 8 9 10 11",
     "numinlets": 1,
     "numoutlets": 13,
     "patching_rect": [
      506,
      150,
      200,
      22
     ],
     "outlettype": [
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      ""
     ]
    }
   },
   {
    "box": {
     "id": "step-lbl",
     "maxclass": "comment",
     "text": "FLAT",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 10.5,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "textjustification": 1,
     "presentation": 1,
     "presentation_rect": [
      10,
      126,
      96,
      16
     ],
     "patching_rect": [
      506,
      240,
      60,
      20
     ]
    }
   },
   {
    "box": {
     "id": "step-m0",
     "maxclass": "message",
     "text": "set FLAT",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      506,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m1",
     "maxclass": "message",
     "text": "set 70",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      552,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m2",
     "maxclass": "message",
     "text": "set 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      598,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m3",
     "maxclass": "message",
     "text": "set 150",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      644,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m4",
     "maxclass": "message",
     "text": "set 250",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      690,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m5",
     "maxclass": "message",
     "text": "set 500",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      736,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m6",
     "maxclass": "message",
     "text": "set 1k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      782,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m7",
     "maxclass": "message",
     "text": "set 2k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      828,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m8",
     "maxclass": "message",
     "text": "set 3k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      874,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m9",
     "maxclass": "message",
     "text": "set 5k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      920,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m10",
     "maxclass": "message",
     "text": "set 7.5k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      966,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step-m11",
     "maxclass": "message",
     "text": "set 10k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      1012,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-rnd",
     "maxclass": "newobj",
     "text": "expr int($f1+0.5)",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      551,
      120,
      110,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "stepr-sel",
     "maxclass": "newobj",
     "text": "sel 0 1 2 3 4 5 6 7 8 9 10 11",
     "numinlets": 1,
     "numoutlets": 13,
     "patching_rect": [
      551,
      150,
      200,
      22
     ],
     "outlettype": [
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      ""
     ]
    }
   },
   {
    "box": {
     "id": "stepr-lbl",
     "maxclass": "comment",
     "text": "FLAT",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.5,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "textjustification": 1,
     "presentation": 1,
     "presentation_rect": [
      106,
      92,
      60,
      14
     ],
     "patching_rect": [
      551,
      240,
      60,
      20
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m0",
     "maxclass": "message",
     "text": "set FLAT",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      551,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m1",
     "maxclass": "message",
     "text": "set 70",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      597,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m2",
     "maxclass": "message",
     "text": "set 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      643,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m3",
     "maxclass": "message",
     "text": "set 150",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      689,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m4",
     "maxclass": "message",
     "text": "set 250",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      735,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m5",
     "maxclass": "message",
     "text": "set 500",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      781,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m6",
     "maxclass": "message",
     "text": "set 1k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      827,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m7",
     "maxclass": "message",
     "text": "set 2k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      873,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m8",
     "maxclass": "message",
     "text": "set 3k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      919,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m9",
     "maxclass": "message",
     "text": "set 5k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      965,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m10",
     "maxclass": "message",
     "text": "set 7.5k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      1011,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "stepr-m11",
     "maxclass": "message",
     "text": "set 10k",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      1057,
      190,
      44,
      22
     ]
    }
   },
   {
    "box": {
     "id": "reso",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      170,
      6,
      48,
      50
     ],
     "patching_rect": [
      254,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.5,
       "parameter_mmax": 8.0,
       "parameter_initial": [
        1.4
       ],
       "parameter_unitstyle": 1,
       "parameter_exponent": 2.0,
       "parameter_longname": "Reso",
       "parameter_shortname": "Reso",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Reso",
       "parameter_info": "Resonance (Q) at the cutoff. 0.707 = no peak.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Reso"
    }
   },
   {
    "box": {
     "id": "reso-p",
     "maxclass": "newobj",
     "text": "prepend reso",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      254,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "drive",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      222,
      6,
      48,
      50
     ],
     "patching_rect": [
      366,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        20.0
       ],
       "parameter_unitstyle": 5,
       "parameter_longname": "Drive",
       "parameter_shortname": "Drive",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Drive",
       "parameter_info": "Console drive, 0..+18 dB into the saturator.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Drive"
    }
   },
   {
    "box": {
     "id": "drive-p",
     "maxclass": "newobj",
     "text": "prepend drive",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      366,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "outlvl",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      274,
      6,
      48,
      50
     ],
     "patching_rect": [
      478,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": -24.0,
       "parameter_mmax": 12.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 4,
       "parameter_longname": "Output",
       "parameter_shortname": "Output",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Output",
       "parameter_info": "Output level in dB.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Output"
    }
   },
   {
    "box": {
     "id": "outlvl-p",
     "maxclass": "newobj",
     "text": "prepend outdb",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      478,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "glide",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      170,
      72,
      48,
      50
     ],
     "patching_rect": [
      590,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 2000.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 2,
       "parameter_exponent": 3.0,
       "parameter_longname": "Glide",
       "parameter_shortname": "Glide",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Glide",
       "parameter_info": "How the cutoff moves between steps: 0 = hard switch, otherwise a glide of this many ms.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Glide"
    }
   },
   {
    "box": {
     "id": "glide-p",
     "maxclass": "newobj",
     "text": "prepend glide",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      590,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "click",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      222,
      72,
      48,
      50
     ],
     "patching_rect": [
      702,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        30.0
       ],
       "parameter_unitstyle": 5,
       "parameter_longname": "Click",
       "parameter_shortname": "Click",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Click",
       "parameter_info": "Level of the switch sound on every step move, at any Glide setting. 0 = silent moves.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Click"
    }
   },
   {
    "box": {
     "id": "click-p",
     "maxclass": "newobj",
     "text": "prepend click",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      702,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "blend",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      274,
      72,
      48,
      50
     ],
     "patching_rect": [
      814,
      60,
      48,
      50
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        100.0
       ],
       "parameter_unitstyle": 5,
       "parameter_longname": "Mix",
       "parameter_shortname": "Mix",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Mix",
       "parameter_info": "Dry/wet.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Mix"
    }
   },
   {
    "box": {
     "id": "blend-p",
     "maxclass": "newobj",
     "text": "prepend blend",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      814,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "motion",
     "maxclass": "live.dial",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      112,
      108,
      48,
      42
     ],
     "patching_rect": [
      926,
      60,
      48,
      42
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 0,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 5,
       "parameter_longname": "Motion",
       "parameter_shortname": "Motion",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Motion",
       "parameter_info": "Resonance blooms while the cutoff is moving and relaxes when it stops. 0 = V2.1 behaviour.",
       "parameter_modmode": 3
      }
     },
     "activedialcolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "dialcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "varname": "Motion"
    }
   },
   {
    "box": {
     "id": "motion-p",
     "maxclass": "newobj",
     "text": "prepend motion",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      926,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "slope-lbl",
     "maxclass": "live.comment",
     "text": "SLOPE",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.0,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "fontface": 0,
     "presentation": 1,
     "presentation_rect": [
      332,
      2,
      84,
      14
     ],
     "patching_rect": [
      700,
      172,
      84,
      18
     ]
    }
   },
   {
    "box": {
     "id": "slope",
     "maxclass": "live.tab",
     "numinlets": 1,
     "numoutlets": 3,
     "outlettype": [
      "",
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      332,
      14,
      84,
      16
     ],
     "patching_rect": [
      1038,
      60,
      84,
      16
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 2,
       "parameter_enum": [
        "12dB",
        "18dB"
       ],
       "parameter_mmax": 1,
       "parameter_initial": [
        1
       ],
       "parameter_longname": "Slope",
       "parameter_shortname": "Slope",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Slope",
       "parameter_info": "12 or 18 dB/octave."
      }
     },
     "activebgoncolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "activetextoncolor": [
      0.1,
      0.1,
      0.1,
      1
     ],
     "bgcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "fontsize": 8.5,
     "varname": "Slope"
    }
   },
   {
    "box": {
     "id": "slope-p",
     "maxclass": "newobj",
     "text": "prepend slope",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      1038,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "stereo-lbl",
     "maxclass": "live.comment",
     "text": "STEREO",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.0,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "fontface": 0,
     "presentation": 1,
     "presentation_rect": [
      332,
      36,
      84,
      14
     ],
     "patching_rect": [
      700,
      178,
      84,
      18
     ]
    }
   },
   {
    "box": {
     "id": "stereo",
     "maxclass": "live.tab",
     "numinlets": 1,
     "numoutlets": 3,
     "outlettype": [
      "",
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      332,
      48,
      84,
      16
     ],
     "patching_rect": [
      1150,
      60,
      84,
      16
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 2,
       "parameter_enum": [
        "Link",
        "Dual",
        "Mono"
       ],
       "parameter_mmax": 2,
       "parameter_initial": [
        0
       ],
       "parameter_longname": "Stereo",
       "parameter_shortname": "Stereo",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Stereo",
       "parameter_info": "Link: one setting, identical L/R. Dual: Filter R sets the right side. Mono: sums L+R first."
      }
     },
     "activebgoncolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "activetextoncolor": [
      0.1,
      0.1,
      0.1,
      1
     ],
     "bgcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "fontsize": 8.5,
     "varname": "Stereo"
    }
   },
   {
    "box": {
     "id": "stereo-p",
     "maxclass": "newobj",
     "text": "prepend stereo",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      1150,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "comp-lbl",
     "maxclass": "live.comment",
     "text": "DRIVE CAL",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.0,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "fontface": 0,
     "presentation": 1,
     "presentation_rect": [
      332,
      70,
      84,
      14
     ],
     "patching_rect": [
      700,
      184,
      84,
      18
     ]
    }
   },
   {
    "box": {
     "id": "comp",
     "maxclass": "live.tab",
     "numinlets": 1,
     "numoutlets": 3,
     "outlettype": [
      "",
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      332,
      82,
      84,
      16
     ],
     "patching_rect": [
      1262,
      60,
      84,
      16
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 2,
       "parameter_enum": [
        "Peak",
        "Unity"
       ],
       "parameter_mmax": 1,
       "parameter_initial": [
        1
       ],
       "parameter_longname": "Drive Cal",
       "parameter_shortname": "Drive Cal",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Drive Cal",
       "parameter_info": "Unity: quiet signals keep their level at any drive. Peak: full-scale stays full-scale, quiet material comes up."
      }
     },
     "activebgoncolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "activetextoncolor": [
      0.1,
      0.1,
      0.1,
      1
     ],
     "bgcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "fontsize": 8.5,
     "varname": "Drive Cal"
    }
   },
   {
    "box": {
     "id": "comp-p",
     "maxclass": "newobj",
     "text": "prepend comp",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      1262,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   },
   {
    "box": {
     "id": "mode-lbl",
     "maxclass": "live.comment",
     "text": "MODE",
     "numinlets": 1,
     "numoutlets": 0,
     "fontsize": 8.0,
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "fontface": 0,
     "presentation": 1,
     "presentation_rect": [
      332,
      104,
      84,
      14
     ],
     "patching_rect": [
      700,
      190,
      84,
      18
     ]
    }
   },
   {
    "box": {
     "id": "mode",
     "maxclass": "live.tab",
     "numinlets": 1,
     "numoutlets": 3,
     "outlettype": [
      "",
      "",
      "float"
     ],
     "parameter_enable": 1,
     "presentation": 1,
     "presentation_rect": [
      332,
      116,
      84,
      16
     ],
     "patching_rect": [
      1374,
      60,
      84,
      16
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_type": 2,
       "parameter_enum": [
        "Filter",
        "Drive"
       ],
       "parameter_mmax": 1,
       "parameter_initial": [
        0
       ],
       "parameter_longname": "Mode",
       "parameter_shortname": "Mode",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Mode",
       "parameter_info": "Drive = filter bypassed, drive stage only."
      }
     },
     "activebgoncolor": [
      0.96,
      0.63,
      0.2,
      1.0
     ],
     "textcolor": [
      0.93,
      0.89,
      0.78,
      1.0
     ],
     "activetextoncolor": [
      0.1,
      0.1,
      0.1,
      1
     ],
     "bgcolor": [
      0.08,
      0.1,
      0.09,
      1.0
     ],
     "fontsize": 8.5,
     "varname": "Mode"
    }
   },
   {
    "box": {
     "id": "mode-p",
     "maxclass": "newobj",
     "text": "prepend drvonly",
     "numinlets": 1,
     "numoutlets": 1,
     "patching_rect": [
      1374,
      290,
      100,
      22
     ],
     "outlettype": [
      ""
     ]
    }
   }
  ],
  "lines": [
   {
    "patchline": {
     "source": [
      "plugin",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "plugin",
      1
     ],
     "destination": [
      "gen",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "gen",
      0
     ],
     "destination": [
      "plugout",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "gen",
      1
     ],
     "destination": [
      "plugout",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      1
     ],
     "destination": [
      "active-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "active-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step",
      0
     ],
     "destination": [
      "step-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "step",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr",
      0
     ],
     "destination": [
      "stepr-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "stepr",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step",
      0
     ],
     "destination": [
      "step-rnd",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-rnd",
      0
     ],
     "destination": [
      "step-sel",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      0
     ],
     "destination": [
      "step-m0",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m0",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      1
     ],
     "destination": [
      "step-m1",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m1",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      2
     ],
     "destination": [
      "step-m2",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m2",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      3
     ],
     "destination": [
      "step-m3",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m3",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      4
     ],
     "destination": [
      "step-m4",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m4",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      5
     ],
     "destination": [
      "step-m5",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m5",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      6
     ],
     "destination": [
      "step-m6",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m6",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      7
     ],
     "destination": [
      "step-m7",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m7",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      8
     ],
     "destination": [
      "step-m8",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m8",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      9
     ],
     "destination": [
      "step-m9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m9",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      10
     ],
     "destination": [
      "step-m10",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m10",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-sel",
      11
     ],
     "destination": [
      "step-m11",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "step-m11",
      0
     ],
     "destination": [
      "step-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr",
      0
     ],
     "destination": [
      "stepr-rnd",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-rnd",
      0
     ],
     "destination": [
      "stepr-sel",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      0
     ],
     "destination": [
      "stepr-m0",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m0",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      1
     ],
     "destination": [
      "stepr-m1",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m1",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      2
     ],
     "destination": [
      "stepr-m2",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m2",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      3
     ],
     "destination": [
      "stepr-m3",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m3",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      4
     ],
     "destination": [
      "stepr-m4",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m4",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      5
     ],
     "destination": [
      "stepr-m5",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m5",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      6
     ],
     "destination": [
      "stepr-m6",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m6",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      7
     ],
     "destination": [
      "stepr-m7",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m7",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      8
     ],
     "destination": [
      "stepr-m8",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m8",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      9
     ],
     "destination": [
      "stepr-m9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m9",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      10
     ],
     "destination": [
      "stepr-m10",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m10",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-sel",
      11
     ],
     "destination": [
      "stepr-m11",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stepr-m11",
      0
     ],
     "destination": [
      "stepr-lbl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "reso",
      0
     ],
     "destination": [
      "reso-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "reso-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "reso",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "drive",
      0
     ],
     "destination": [
      "drive-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "drive-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "drive",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "outlvl",
      0
     ],
     "destination": [
      "outlvl-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "outlvl-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "outlvl",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "glide",
      0
     ],
     "destination": [
      "glide-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "glide-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "glide",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "click",
      0
     ],
     "destination": [
      "click-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "click-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "click",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "blend",
      0
     ],
     "destination": [
      "blend-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "blend-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "blend",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "motion",
      0
     ],
     "destination": [
      "motion-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "motion-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "motion",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "slope",
      0
     ],
     "destination": [
      "slope-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "slope-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "slope",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stereo",
      0
     ],
     "destination": [
      "stereo-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "stereo-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "stereo",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "comp",
      0
     ],
     "destination": [
      "comp-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "comp-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "comp",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "mode",
      0
     ],
     "destination": [
      "mode-p",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "mode-p",
      0
     ],
     "destination": [
      "gen",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "thisdev",
      0
     ],
     "destination": [
      "mode",
      0
     ]
    }
   }
  ],
  "parameters": {
   "step": [
    "Tubby Filter",
    "Filter",
    0
   ],
   "stepr": [
    "Filter R",
    "Filter R",
    0
   ],
   "reso": [
    "Reso",
    "Reso",
    0
   ],
   "drive": [
    "Drive",
    "Drive",
    0
   ],
   "outlvl": [
    "Output",
    "Output",
    0
   ],
   "glide": [
    "Glide",
    "Glide",
    0
   ],
   "click": [
    "Click",
    "Click",
    0
   ],
   "blend": [
    "Mix",
    "Mix",
    0
   ],
   "motion": [
    "Motion",
    "Motion",
    0
   ],
   "slope": [
    "Slope",
    "Slope",
    0
   ],
   "stereo": [
    "Stereo",
    "Stereo",
    0
   ],
   "comp": [
    "Drive Cal",
    "Drive Cal",
    0
   ],
   "mode": [
    "Mode",
    "Mode",
    0
   ],
   "parameterbanks": {
    "0": {
     "index": 0,
     "name": "Perform",
     "parameters": [
      "Tubby Filter",
      "Reso",
      "Drive",
      "Output",
      "Glide",
      "Click",
      "Mix",
      "Motion"
     ]
    },
    "1": {
     "index": 1,
     "name": "Setup",
     "parameters": [
      "Filter R",
      "Slope",
      "Stereo",
      "Drive Cal",
      "Mode",
      "-",
      "-",
      "-"
     ]
    }
   },
   "inherited_shortname": 1
  },
  "latency": 0
 }
}