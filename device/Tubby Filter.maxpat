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
  "description": "Tubby Filter v2 \u2014 stepped dub high-pass with console drive",
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
     "text": "stepped hi-pass \u00b7 console drive",
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
      200,
      14
     ],
     "patching_rect": [
      700,
      64,
      200,
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
     "text": "gen~ @title tubby_v2",
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
         "code": "// =====================================================================\n//  Tubby Filter v2 \u2014 gen~ codebox (in1/in2 -> out1/out2)\n//  Stepped dub high-pass with console drive, inspired by the switched\n//  high-pass on King Tubby's desk. Character model, not a circuit clone.\n//\n//  Signal flow per channel:\n//   input -> [stereo mode] -> DRIVE (tanh + bias, calibrated, DC block)\n//         -> HP 2-pole TPT SVF (+ optional 1-pole => 18 dB/oct)\n//         -> FLAT/IN crossfade -> dry/wet MIX -> OUTPUT gain\n//         -> + switch transient -> safety soft-knee -> NaN guard\n//\n//  All time constants are in ms or Hz, so behaviour is the same at\n//  any sample rate. All recursive states pass fixdenorm()/fixnan().\n// =====================================================================\n\n// ---- v1 parameters (same names and ranges, kept for compatibility)\nParam knob(0, min=0, max=11);      // left/linked step: 0 = FLAT, 1..11\nParam reso(1.4, min=0.5, max=8);   // Q\nParam drive(20, min=0, max=100);   // % drive (0..+18 dB into the shaper)\nParam glide(0, min=0, max=2000);   // ms; 0 = hard switched\nParam click(30, min=0, max=100);   // % switch transient\nParam slope(1, min=0, max=1);      // 0 = 12 dB/oct, 1 = 18 dB/oct\nParam blend(100, min=0, max=100);  // % dry/wet\n\n// ---- v2 parameters\nParam knobr(0, min=0, max=11);     // right step (Dual mode only)\nParam stereo(0, min=0, max=2);     // 0 Linked, 1 Dual, 2 Mono\nParam comp(1, min=0, max=1);       // 1 Unity (small-signal) / 0 Peak calibration\nParam drvonly(0, min=0, max=1);    // 1 = filter bypassed, drive only\nParam outdb(0, min=-24, max=12);   // output level, dB\n\n// ---------------------------------------------------------------------\n// one-pole smoother, time constant in ms (sample-rate independent)\nslew(x, ms) {\n    History y(0);\n    c = 1 - exp(-1 / (max(ms, 0.01) * 0.001 * samplerate));\n    n = fixnan(fixdenorm(y + (x - y) * c));\n    y = n;\n    return n;\n}\n\n// TPT (zero-delay feedback) state-variable high-pass, Zavalishin form.\n// Stable for any k > 0 and any g >= 0, so modulation cannot blow it up.\nsvf_hp(x, g, k) {\n    History ic1(0), ic2(0);\n    a1 = 1 / (1 + g * (g + k));\n    a2 = g * a1;\n    a3 = g * a2;\n    v3 = x - ic2;\n    v1 = a1 * ic1 + a2 * v3;\n    v2 = ic2 + a2 * ic1 + a3 * v3;\n    ic1 = fixnan(fixdenorm(2 * v1 - ic1));\n    ic2 = fixnan(fixdenorm(2 * v2 - ic2));\n    return x - k * v1 - v2;\n}\n\n// TPT one-pole high-pass (the extra 6 dB/oct for the 18 dB slope)\nop_hp(x, g) {\n    History s(0);\n    G = g / (1 + g);\n    v = (x - s) * G;\n    lp = v + s;\n    s = fixnan(fixdenorm(lp + v));\n    return x - lp;\n}\n\n// one-pole low-pass with cutoff in Hz (used to colour the click noise)\nop_lp(x, hz) {\n    History s(0);\n    c = 1 - exp(-twopi * hz / samplerate);\n    n = fixdenorm(s + (x - s) * c);\n    s = n;\n    return n;\n}\n\n// 5 Hz DC blocker (the asymmetric drive creates a little DC)\ndcblock(x) {\n    History xp(0), yp(0);\n    r = exp(-twopi * 5 / samplerate);\n    y = fixnan(fixdenorm(x - xp + r * yp));\n    xp = x;\n    yp = y;\n    return y;\n}\n\n// step index -> cutoff Hz (index 0 = FLAT, parked at 20 Hz)\nstepfreq(i) {\n    return selector(i + 1, 20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000);\n}\n\n// switch transient: three decaying bursts (contact bounce), times in s\nbounce(t) {\n    tau = 0.0007;\n    e1 = exp(-t / tau);\n    e2 = t >= 0.0011 ? 0.45 * exp(-(t - 0.0011) / tau) : 0;\n    e3 = t >= 0.0026 ? 0.20 * exp(-(t - 0.0026) / tau) : 0;\n    return t < 0.02 ? e1 + e2 + e3 : 0;\n}\n\n// asymmetric console drive.\n//   s(x)  = tanh(G*x + b) - tanh(b)            zero in -> zero out\n//   s'(0) = G * (1 - tanh(b)^2)                 small-signal gain\n//   span  = (tanh(G + b) - tanh(b - G)) / 2     mean full-scale output\n//   Comp on  (\"Unity\"): y = s(x) / s'(0)  -> small-signal gain exactly 1\n//   Comp off (\"Peak\") : y = s(x) / span   -> a 0 dBFS input stays near\n//                       0 dBFS; quiet material comes up (pushed desk)\ndrive_stage(x, G, b, cmp, amt) {\n    tb = tanh(b);\n    sh = tanh(G * x + b) - tb;\n    s0 = G * (1 - tb * tb);\n    sp = (tanh(G + b) - tanh(b - G)) * 0.5;\n    y = cmp > 0.5 ? sh / s0 : sh / sp;\n    return mix(x, dcblock(y), amt);\n}\n\n// ---------------------------------------------------------------------\nHistory lfL(2.9957), lfR(2.9957);  // smoothed log(Hz) per channel (log 20)\nHistory wL(0), wR(0);              // filter-in weight per channel\nHistory pL(0), pR(0);              // previous step per channel\nHistory tL(1), tR(1);              // seconds since last switch per channel\nHistory age(0);                    // seconds since device load\n\nsr = samplerate;\nnage = min(age + 1 / sr, 1);\nage = nage;\n\n// ---- smoothed continuous controls (20 ms)\nq   = max(slew(reso, 20), 0.5);\nd   = clamp(slew(drive, 20), 0, 100) * 0.01;\nsl  = clamp(slew(slope, 10), 0, 1);\nbl  = clamp(slew(blend, 20), 0, 100) * 0.01;\nog  = slew(dbtoa(outdb), 20);\ncp  = comp;\nmode = floor(stereo + 0.5);\n\n// ---- input routing\nmono = (in1 + in2) * 0.5;\nxL = mode == 2 ? mono : in1;\nxR = mode == 2 ? mono : in2;\n\n// ---- drive: 0..+18 dB pre-gain, bias grows with drive (even harmonics)\nG   = dbtoa(d * 18);\nb   = 0.25 * d;\namt = clamp(d * 8, 0, 1);          // drive 0 = true clean path\ndL = drive_stage(xL, G, b, cp, amt);\ndR = drive_stage(xR, G, b, cp, amt);\n\n// ---- step selection\niL = clamp(floor(knob + 0.5), 0, 11);\niR = mode == 1 ? clamp(floor(knobr + 0.5), 0, 11) : iL;\n\n// frequency slew: hard (0.5 ms floor so every rate sees the same step\n// shape), or glide in ms, done in the log domain so it sounds even\ngms = max(glide, 0.5);\ncg  = 1 - exp(-1 / (gms * 0.001 * sr));\nnlL = lfL + (log(stepfreq(iL)) - lfL) * cg;\nnlR = lfR + (log(stepfreq(iR)) - lfR) * cg;\nlfL = nlL;\nlfR = nlR;\nfcL = clamp(exp(nlL), 10, sr * 0.45);\nfcR = clamp(exp(nlR), 10, sr * 0.45);\n\n// FLAT <-> filter crossfade, follows glide but never faster than 4 ms\nbyp = drvonly > 0.5;\ncw  = 1 - exp(-1 / (max(4, glide) * 0.001 * sr));\nnwL = wL + (((iL > 0) * (1 - byp)) - wL) * cw;\nnwR = wR + (((iR > 0) * (1 - byp)) - wR) * cw;\nwL = nwL;\nwR = nwR;\n\n// ---- filters\nk  = 1 / q;\ngL = tan(pi * fcL / sr);\ngR = tan(pi * fcR / sr);\nhL = svf_hp(dL, gL, k);\nhR = svf_hp(dR, gR, k);\nfL = mix(hL, op_hp(hL, gL), sl);\nfR = mix(hR, op_hp(hR, gR), sl);\n\nyL = mix(dL, fL, nwL);\nyR = mix(dR, fR, nwR);\n\n// ---- dry/wet and output gain\noL = mix(xL, yL, bl) * og;\noR = mix(xR, yR, bl) * og;\n\n// ---- switch transient (only in hard-switch mode, not in drive-only)\nchL = iL != pL;\nchR = iR != pR;\npL = iL;\npR = iR;\nntL = chL ? 0 : min(tL + 1 / sr, 1);\nntR = chR ? 0 : min(tR + 1 / sr, 1);\ntL = ntL;\ntR = ntR;\n// band-limited noise 500 Hz..5 kHz, level normalised for sample rate\nnz  = noise() * sqrt(sr / 44100);\nnb  = op_lp(nz, 5000);\nnb  = nb - op_lp(nb, 500);\n// (muted for the first 200 ms so restoring a saved step doesn't click)\ncgn = click * 0.01 * 0.5 * (glide < 1) * (1 - byp) * (nage > 0.2);\noL = oL + nb * bounce(ntL) * cgn * og;\noR = oR + nb * bounce(ntR) * cgn * og;\n\n// ---- safety: bit-transparent below +6 dBFS, soft knee to a +8 dBFS\n// ceiling (Live runs in float, so normal levels pass untouched; this only\n// catches runaway resonance + drive + Output +12 dB)\nth = 1.9953;\nkn = 0.5166;\naL = abs(oL);\naR = abs(oR);\noL = aL > th ? sign(oL) * (th + kn * tanh((aL - th) / kn)) : oL;\noR = aR > th ? sign(oR) * (th + kn * tanh((aR - th) / kn)) : oR;\n\nout1 = fixnan(oL);\nout2 = fixnan(oR);\n",
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
       "parameter_type": 2,
       "parameter_enum": [
        "FLAT",
        "70",
        "100",
        "150",
        "250",
        "500",
        "1k",
        "2k",
        "3k",
        "5k",
        "7.5k",
        "10k"
       ],
       "parameter_mmax": 11,
       "parameter_initial": [
        0
       ],
       "parameter_longname": "Tubby Filter",
       "parameter_shortname": "Filter",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Tubby Filter",
       "parameter_info": "Stepped high-pass cutoff. FLAT = filter out. Linked/Mono: both sides; Dual: left side."
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
     ]
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
       "parameter_type": 2,
       "parameter_enum": [
        "FLAT",
        "70",
        "100",
        "150",
        "250",
        "500",
        "1k",
        "2k",
        "3k",
        "5k",
        "7.5k",
        "10k"
       ],
       "parameter_mmax": 11,
       "parameter_initial": [
        0
       ],
       "parameter_longname": "Filter R",
       "parameter_shortname": "Filter R",
       "parameter_initial_enable": 1,
       "parameter_annotation_name": "Filter R",
       "parameter_info": "Right-side cutoff. Active only in Dual stereo mode."
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
     ]
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
       "parameter_info": "Resonance (Q) at the cutoff. 0.707 = no peak."
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
     ]
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
       "parameter_info": "Console drive, 0..+18 dB into the saturator."
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
     ]
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
       "parameter_info": "Output level in dB."
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
     ]
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
       "parameter_info": "0 = hard switched (with switch transient). Above 0: steps glide over this many ms, no transient."
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
     ]
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
       "parameter_info": "Switch transient level (hard-switch mode only)."
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
     ]
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
       "parameter_info": "Dry/wet."
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
     ]
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
      106,
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
      926,
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
     "fontsize": 8.5
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
      112,
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
      1038,
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
     "fontsize": 8.5
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
      118,
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
      1150,
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
     "fontsize": 8.5
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
      124,
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
      1262,
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
     "fontsize": 8.5
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
      1262,
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
  ]
 }
}