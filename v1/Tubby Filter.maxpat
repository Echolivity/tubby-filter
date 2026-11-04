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
   100,
   100,
   900,
   480
  ],
  "openinpresentation": 1,
  "devicewidth": 345.0,
  "boxes": [
   {
    "box": {
     "id": "plugin",
     "maxclass": "newobj",
     "text": "plugin~",
     "numinlets": 2,
     "numoutlets": 2,
     "outlettype": [
      "signal",
      "signal"
     ],
     "patching_rect": [
      30,
      260,
      60,
      22
     ]
    }
   },
   {
    "box": {
     "id": "gen",
     "maxclass": "newobj",
     "text": "gen~ @title tubby",
     "numinlets": 2,
     "numoutlets": 2,
     "outlettype": [
      "signal",
      "signal"
     ],
     "patching_rect": [
      30,
      320,
      200,
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
       100,
       100,
       700,
       600
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
          30,
          20,
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
          400,
          20,
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
         "code": "// King Tubby-style stepped high-pass filter (gen~ codebox)\n// Modeled on the Altec 9069B passive filter on Tubby's MCI board:\n// 11 switched positions, no smooth sweep, audible click on each step.\n\nParam knob(0, min=0, max=11);      // 0 = flat, 1..11 = 70 Hz .. 10 kHz\nParam reso(1.4, min=0.5, max=8);   // Q of the 2-pole section\nParam drive(20, min=0, max=100);   // % console overdrive before the filter\nParam glide(0, min=0, max=2000);   // ms; 0 = hard switched like the original\nParam click(30, min=0, max=100);   // % switch click level\nParam slope(1, min=0, max=1);      // 0 = 12 dB/oct, 1 = 18 dB/oct\nParam blend(100, min=0, max=100);  // % dry/wet\n\n// TPT state-variable high-pass (2-pole, resonant)\nsvf_hp(x, g, k) {\n    History ic1(0), ic2(0);\n    a1 = 1 / (1 + g * (g + k));\n    a2 = g * a1;\n    a3 = g * a2;\n    v3 = x - ic2;\n    v1 = a1 * ic1 + a2 * v3;\n    v2 = ic2 + a2 * ic1 + a3 * v3;\n    ic1 = 2 * v1 - ic1;\n    ic2 = 2 * v2 - ic2;\n    return x - k * v1 - v2;\n}\n\n// TPT one-pole high-pass (adds the extra 6 dB/oct)\nop_hp(x, g) {\n    History s(0);\n    G = g / (1 + g);\n    v = (x - s) * G;\n    lp = v + s;\n    s = lp + v;\n    return x - lp;\n}\n\nHistory lf(3);     // smoothed log-frequency\nHistory wt(0);     // filter engaged amount (0 = flat)\nHistory prev(0);   // previous switch position\nHistory env(0);    // click envelope\n\nidx = clamp(floor(knob + 0.5), 0, 11);\nfsel = selector(idx + 1, 20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000);\n\n// frequency: instant jump by default, optional log-domain glide\nkg = glide > 0.5 ? 1 - exp(-1 / (glide * 0.001 * samplerate)) : 1;\nnlf = lf + (log(fsel) - lf) * kg;\nlf = nlf;\nfc = clamp(exp(nlf), 10, samplerate * 0.45);\n\n// short crossfade when switching to/from FLAT\non = idx > 0;\nnwt = wt + (on - wt) * (1 - exp(-1 / (0.004 * samplerate)));\nwt = nwt;\n\n// switch click: short noise burst whenever the position changes\nne = idx != prev ? click * 0.01 : env * exp(-1 / (0.0025 * samplerate));\nenv = ne;\nprev = idx;\nclk = noise() * ne * 0.15;\n\n// console drive (unity at low level, soft ceiling when pushed)\ndg = 1 + drive * 0.03;\ndL = tanh(in1 * dg) / sqrt(dg);\ndR = tanh(in2 * dg) / sqrt(dg);\n\ng = tan(pi * fc / samplerate);\nk = 1 / reso;\n\nhL = svf_hp(dL, g, k);\nhR = svf_hp(dR, g, k);\nfL = mix(hL, op_hp(hL, g), slope);\nfR = mix(hR, op_hp(hR, g), slope);\n\nwL = mix(dL, fL, nwt);\nwR = mix(dR, fR, nwt);\n\nb = blend * 0.01;\nout1 = mix(in1, wL, b) + clk;\nout2 = mix(in2, wR, b) + clk;\n",
         "fontface": 0,
         "fontname": "<Monospaced>",
         "fontsize": 12,
         "numinlets": 2,
         "numoutlets": 2,
         "outlettype": [
          "",
          ""
         ],
         "patching_rect": [
          30,
          60,
          600,
          440
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
          30,
          520,
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
          400,
          520,
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
      380,
      60,
      22
     ]
    }
   },
   {
    "box": {
     "id": "step",
     "maxclass": "live.menu",
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
      10,
      8,
      70,
      20
     ],
     "patching_rect": [
      30,
      40,
      70,
      20
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Tubby Filter",
       "parameter_shortname": "Filter",
       "parameter_type": 2,
       "parameter_initial_enable": 1,
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
       ]
      }
     }
    }
   },
   {
    "box": {
     "id": "step-p",
     "maxclass": "newobj",
     "text": "prepend knob",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      30,
      200,
      90,
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
      90,
      8,
      44,
      48
     ],
     "patching_rect": [
      135,
      40,
      44,
      48
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Reso",
       "parameter_shortname": "Reso",
       "parameter_type": 0,
       "parameter_initial_enable": 1,
       "parameter_mmin": 0.5,
       "parameter_mmax": 8.0,
       "parameter_initial": [
        1.4
       ],
       "parameter_unitstyle": 1
      }
     }
    }
   },
   {
    "box": {
     "id": "reso-p",
     "maxclass": "newobj",
     "text": "prepend reso",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      135,
      200,
      90,
      22
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
      140,
      8,
      44,
      48
     ],
     "patching_rect": [
      240,
      40,
      44,
      48
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Drive",
       "parameter_shortname": "Drive",
       "parameter_type": 0,
       "parameter_initial_enable": 1,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        20.0
       ],
       "parameter_unitstyle": 5
      }
     }
    }
   },
   {
    "box": {
     "id": "drive-p",
     "maxclass": "newobj",
     "text": "prepend drive",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      240,
      200,
      90,
      22
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
      190,
      8,
      44,
      48
     ],
     "patching_rect": [
      345,
      40,
      44,
      48
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Glide",
       "parameter_shortname": "Glide",
       "parameter_type": 0,
       "parameter_initial_enable": 1,
       "parameter_mmin": 0.0,
       "parameter_mmax": 2000.0,
       "parameter_initial": [
        0.0
       ],
       "parameter_unitstyle": 2
      }
     }
    }
   },
   {
    "box": {
     "id": "glide-p",
     "maxclass": "newobj",
     "text": "prepend glide",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      345,
      200,
      90,
      22
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
      240,
      8,
      44,
      48
     ],
     "patching_rect": [
      450,
      40,
      44,
      48
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Click",
       "parameter_shortname": "Click",
       "parameter_type": 0,
       "parameter_initial_enable": 1,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        30.0
       ],
       "parameter_unitstyle": 5
      }
     }
    }
   },
   {
    "box": {
     "id": "click-p",
     "maxclass": "newobj",
     "text": "prepend click",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      450,
      200,
      90,
      22
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
      290,
      8,
      44,
      48
     ],
     "patching_rect": [
      555,
      40,
      44,
      48
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Mix",
       "parameter_shortname": "Mix",
       "parameter_type": 0,
       "parameter_initial_enable": 1,
       "parameter_mmin": 0.0,
       "parameter_mmax": 100.0,
       "parameter_initial": [
        100.0
       ],
       "parameter_unitstyle": 5
      }
     }
    }
   },
   {
    "box": {
     "id": "blend-p",
     "maxclass": "newobj",
     "text": "prepend blend",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      555,
      200,
      90,
      22
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
      10,
      36,
      70,
      20
     ],
     "patching_rect": [
      660,
      40,
      70,
      20
     ],
     "saved_attribute_attributes": {
      "valueof": {
       "parameter_longname": "Slope",
       "parameter_shortname": "Slope",
       "parameter_type": 2,
       "parameter_initial_enable": 1,
       "parameter_enum": [
        "12 dB",
        "18 dB"
       ],
       "parameter_mmax": 1,
       "parameter_initial": [
        1
       ]
      }
     }
    }
   },
   {
    "box": {
     "id": "slope-p",
     "maxclass": "newobj",
     "text": "prepend slope",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      660,
      200,
      90,
      22
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
   }
  ]
 }
}