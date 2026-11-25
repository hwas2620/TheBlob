# verify8 판정 출력 (judge.py 자동 생성)

| 주장 | 판정 |
|---|---|
| c1 | 맞음 |
| c2 | 판정 못 함 |
| c3 | 맞음 |
| c4 | 맞음 |
| c5 | 맞음 |
| c6 | 맞음 |
| c7 | 틀림 |
| c8 | 맞음 |
| c9 | 맞음 |

```
{
 "c1": {
  "verdict": "맞음",
  "v8c": {
   "runs": 39,
   "mean_per_snap": 23.336,
   "frac_snaps": 0.781,
   "snaps": 1146,
   "by_scn": {
    "asym3": 20.9375,
    "food3": 24.1648,
    "food4": 47.1818,
    "long": 68.9082,
    "mig": 12.8194,
    "slimeall": 0.0
   },
   "runs_with_crumb": 35
  },
  "v8v": {
   "runs": 43,
   "mean_per_snap": 0.0,
   "frac_snaps": 0.0,
   "snaps": 1298,
   "by_scn": {
    "asym3": 0.0,
    "food3": 0.0,
    "food4": 0.0,
    "long": 0.0,
    "mig": 0.0,
    "slimeall": 0.0
   },
   "runs_with_crumb": 0
  }
 },
 "c2": {
  "verdict": "판정 못 함",
  "why": "중간(0.5~0.8배) 또는 짝 비교·분열 포함 조건 어긋남",
  "agg": {
   "c_db": 0.1123,
   "v_db": 0.0428,
   "c_db_d2": 0.1377,
   "v_db_d2": 0.0457,
   "c_thick": 0.1116,
   "v_thick": 0.0153,
   "c_fis": 0.0483,
   "v_fis": 0.0,
   "c_split": 0.1232,
   "v_split": 0.0428
  },
  "pairs_worse": 3,
  "pairs_nontie": 9
 },
 "c3": {
  "verdict": "맞음",
  "sub": {
   "threads": "맞음",
   "tips": "맞음"
  },
  "measures": {
   "nf_thread_0.05": {
    "ctrl_mean": 37.2352,
    "cand_mean": 2.5468,
    "ratio": 0.0684,
    "pairs_lower": 35,
    "pairs_nontie": 37
   },
   "nf_tipr_0.05": {
    "ctrl_mean": 11.7553,
    "cand_mean": 0.2785,
    "ratio": 0.0237,
    "pairs_lower": 35,
    "pairs_nontie": 37
   },
   "nf_tipc_0.05": {
    "ctrl_mean": 20.1887,
    "cand_mean": 0.0223,
    "ratio": 0.0011,
    "pairs_lower": 35,
    "pairs_nontie": 35
   },
   "nf_thread_0.01": {
    "ctrl_mean": 30.478,
    "cand_mean": 0.1066,
    "ratio": 0.0035,
    "pairs_lower": 35,
    "pairs_nontie": 35
   },
   "nf_thread_0.2": {
    "ctrl_mean": 67.6109,
    "cand_mean": 30.6647,
    "ratio": 0.4535,
    "pairs_lower": 29,
    "pairs_nontie": 39
   },
   "nf_tipr_0.01": {
    "ctrl_mean": 10.9595,
    "cand_mean": 0.0142,
    "ratio": 0.0013,
    "pairs_lower": 35,
    "pairs_nontie": 35
   },
   "nf_tipr_0.2": {
    "ctrl_mean": 13.0046,
    "cand_mean": 0.9269,
    "ratio": 0.0713,
    "pairs_lower": 35,
    "pairs_nontie": 37
   },
   "thread_cells": {
    "ctrl_mean": 625.6697,
    "cand_mean": 755.8946,
    "ratio": 1.2081,
    "pairs_lower": 15,
    "pairs_nontie": 39
   },
   "tips_robust": {
    "ctrl_mean": 16.254,
    "cand_mean": 2.2139,
    "ratio": 0.1362,
    "pairs_lower": 35,
    "pairs_nontie": 39
   }
  },
  "film": {
   "ctrl_mean": 516.1285,
   "cand_mean": 428.2285,
   "ratio": 0.8297,
   "verdict": "맞음"
  },
  "by_scn": {
   "asym3": {
    "c_thr": 17.108,
    "v_thr": 3.3693,
    "c_tip": 8.5454,
    "v_tip": 0.1818,
    "n": 8
   },
   "food3": {
    "c_thr": 29.3182,
    "v_thr": 3.2443,
    "c_tip": 10.1705,
    "v_tip": 0.2955,
    "n": 8
   },
   "food4": {
    "c_thr": 78.5985,
    "v_thr": 6.0076,
    "c_tip": 21.2879,
    "v_tip": 0.8334,
    "n": 4
   },
   "long": {
    "c_thr": 171.3265,
    "v_thr": 1.3708,
    "c_tip": 45.7857,
    "v_tip": 0.3674,
    "n": 3
   },
   "mig": {
    "c_thr": 21.0324,
    "v_thr": 1.5185,
    "c_tip": 7.1852,
    "v_tip": 0.213,
    "n": 12
   },
   "slimeall": {
    "c_thr": 0.0,
    "v_thr": 0.0132,
    "c_tip": 0.0,
    "v_tip": 0.0132,
    "n": 4
   }
  }
 },
 "c4": {
  "verdict": "맞음",
  "a": {
   "ctrl": 63,
   "cand": 64,
   "foods": 64,
   "deficit": -1,
   "verdict": "맞음"
  },
  "b": {
   "median_ratio": 1.0032,
   "n": 20,
   "censored_cand": 0,
   "censored_ctrl": 1,
   "delays_over_20": 2,
   "max_delay": 181.4,
   "verdict": "맞음"
  },
  "c": {
   "n": 15,
   "t_med_c": 244.8,
   "t_med_v": 236.4,
   "hit_c": 15,
   "hit_v": 15,
   "d_med_c": 71.96,
   "d_med_v": 76.41,
   "d200_med_c": 27.34,
   "d200_med_v": 34.41,
   "t_ratio": 0.9657,
   "d_ratio": 1.0618,
   "verdict": "맞음"
  }
 },
 "c5": {
  "verdict": "맞음",
  "v8c": {
   "n": 15,
   "med_abs": 2.45,
   "mean_signed": -1.73,
   "n_pos": 6,
   "n_neg": 9,
   "p_side": 0.6072,
   "rows": [
    {
     "scn": "long",
     "seed": 821,
     "err": 1.04,
     "t": 240.0,
     "at": "35"
    },
    {
     "scn": "long",
     "seed": 822,
     "err": -8.89,
     "t": 220.0,
     "at": "35"
    },
    {
     "scn": "long",
     "seed": 823,
     "err": -0.59,
     "t": 260.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 801,
     "err": 3.95,
     "t": 240.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 802,
     "err": -5.43,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 803,
     "err": -11.07,
     "t": 220.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 804,
     "err": 1.08,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 805,
     "err": -4.61,
     "t": 240.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 806,
     "err": 6.63,
     "t": 235.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 807,
     "err": 2.1,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 808,
     "err": -6.53,
     "t": 235.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 809,
     "err": 1.05,
     "t": 245.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 810,
     "err": -1.26,
     "t": 245.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 811,
     "err": -2.45,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 812,
     "err": -0.97,
     "t": 225.0,
     "at": "35"
    }
   ]
  },
  "v8v": {
   "n": 15,
   "med_abs": 8.03,
   "mean_signed": 1.85,
   "n_pos": 7,
   "n_neg": 8,
   "p_side": 1.0,
   "rows": [
    {
     "scn": "long",
     "seed": 821,
     "err": -0.23,
     "t": 205.0,
     "at": "35"
    },
    {
     "scn": "long",
     "seed": 822,
     "err": 15.39,
     "t": 210.0,
     "at": "35"
    },
    {
     "scn": "long",
     "seed": 823,
     "err": 3.29,
     "t": 210.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 801,
     "err": -8.27,
     "t": 185.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 802,
     "err": -11.37,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 803,
     "err": -3.19,
     "t": 195.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 804,
     "err": 2.9,
     "t": 200.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 805,
     "err": -7.88,
     "t": 215.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 806,
     "err": -18.51,
     "t": 195.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 807,
     "err": 9.93,
     "t": 210.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 808,
     "err": 25.87,
     "t": 205.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 809,
     "err": -3.52,
     "t": 190.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 810,
     "err": -3.46,
     "t": 205.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 811,
     "err": 8.03,
     "t": 225.0,
     "at": "35"
    },
    {
     "scn": "mig",
     "seed": 812,
     "err": 18.83,
     "t": 210.0,
     "at": "35"
    }
   ]
  }
 },
 "c6": {
  "verdict": "맞음",
  "why": "",
  "agg": {
   "cells": {
    "ctrl": 51.4705,
    "cand": 3.3031,
    "ratio": 0.0642
   },
   "maxlen": {
    "ctrl": 8.8393,
    "cand": 2.3161,
    "ratio": 0.262
   },
   "n3": {
    "ctrl": 5.1232,
    "cand": 0.3837,
    "ratio": 0.0749
   },
   "rob_old": {
    "ctrl": 32.7574,
    "cand": 12.5831,
    "ratio": 0.3841
   },
   "rob_old_max": {
    "ctrl": 11.8012,
    "cand": 7.3705,
    "ratio": 0.6246
   },
   "rob": {
    "ctrl": 32.7693,
    "cand": 12.5987,
    "ratio": 0.3845
   },
   "head_n": {
    "ctrl": 0.0359,
    "cand": 0.065,
    "ratio": 1.8106
   },
   "head_cells": {
    "ctrl": 16.2685,
    "cand": 42.8634,
    "ratio": 2.6347
   },
   "head_max": {
    "ctrl": 16.2685,
    "cand": 42.8634,
    "ratio": 2.6347
   },
   "loop_n": {
    "ctrl": 1.4031,
    "cand": 0.5029,
    "ratio": 0.3584
   },
   "loop_cells": {
    "ctrl": 77.1262,
    "cand": 41.9485,
    "ratio": 0.5439
   },
   "loop_max": {
    "ctrl": 65.9371,
    "cand": 39.7146,
    "ratio": 0.6023
   },
   "tube_n": {
    "ctrl": 6.3068,
    "cand": 6.7445,
    "ratio": 1.0694
   },
   "tube_cells": {
    "ctrl": 549.504,
    "cand": 980.0188,
    "ratio": 1.7835
   },
   "tube_max": {
    "ctrl": 261.5492,
    "cand": 462.2003,
    "ratio": 1.7672
   },
   "snaps": {
    "ctrl": 23.6,
    "cand": 23.35,
    "ratio": 0.9894
   }
  },
  "pairs_lower": 20,
  "pairs_nontie": 20,
  "robust_note": "굳센 정의(열림 기준 매달린 실, 오래된 것)도 0.5배 이하"
 },
 "c7": {
  "verdict": "틀림",
  "sub": {
   "a": "맞음",
   "a_fail": [],
   "b": "판정 못 함",
   "b_fail": [
    "b_long_s823_v8v"
   ],
   "c": "맞음",
   "c_fail": [],
   "d": "틀림",
   "d_fail": [
    "b_long_s823_v8v",
    "b_slimeall_s861_v8v",
    "b_slimeall_s862_v8v",
    "b_slimeall_s863_v8v",
    "b_slimeall_s864_v8v",
    "b_slimeall_s865_v8v",
    "b_slimeall_s866_v8v",
    "b_slimeall_s867_v8v",
    "b_slimeall_s868_v8v"
   ],
   "e": "맞음",
   "e_fail": [],
   "f": "틀림",
   "f_fail": [
    "b_slimeall_s861_v8v",
    "b_slimeall_s863_v8v"
   ]
  },
  "qualified": 10,
  "slime_without_scl": [],
  "pair_iou_median": 0.5262,
  "at_min_area": 2
 },
 "c8": {
  "verdict": "맞음",
  "n": 43,
  "bad": [],
  "worst": {
   "mass_err_max": 1.928615997063129e-13,
   "h_min_end": 0.0,
   "h_min_seen": 0.0,
   "V_crumb_max": 0
  }
 },
 "c9": {
  "verdict": "맞음",
  "v8c": {
   "n": 12240,
   "median": 0.06349,
   "p90": 0.1512,
   "p99": 0.31712,
   "max": 0.89434
  },
  "v8c_by": {
   "asym3": {
    "n": 1920,
    "median": 0.08402,
    "p99": 0.36424,
    "max": 0.89434
   },
   "food3": {
    "n": 1920,
    "median": 0.07506,
    "p99": 0.35805,
    "max": 0.78182
   },
   "food4": {
    "n": 1400,
    "median": 0.03683,
    "p99": 0.21013,
    "max": 0.33683
   },
   "long": {
    "n": 3000,
    "median": 0.05931,
    "p99": 0.2349,
    "max": 0.49264
   },
   "mig": {
    "n": 2400,
    "median": 0.06023,
    "p99": 0.20124,
    "max": 0.30071
   },
   "slimeall": {
    "n": 1600,
    "median": 0.07169,
    "p99": 0.43635,
    "max": 0.7911
   }
  },
  "v8v": {
   "n": 13840,
   "median": 0.02794,
   "p90": 0.06362,
   "p99": 0.12196,
   "max": 0.27327
  },
  "v8v_by": {
   "asym3": {
    "n": 1920,
    "median": 0.03761,
    "p99": 0.13018,
    "max": 0.20872
   },
   "food3": {
    "n": 1920,
    "median": 0.03395,
    "p99": 0.13503,
    "max": 0.26893
   },
   "food4": {
    "n": 1400,
    "median": 0.01574,
    "p99": 0.06565,
    "max": 0.12295
   },
   "long": {
    "n": 3000,
    "median": 0.03095,
    "p99": 0.13132,
    "max": 0.27327
   },
   "mig": {
    "n": 2400,
    "median": 0.03133,
    "p99": 0.10484,
    "max": 0.19568
   },
   "slimeall": {
    "n": 3200,
    "median": 0.01448,
    "p99": 0.12698,
    "max": 0.25634
   }
  },
  "ratios": [
   0.4401,
   0.4208,
   0.3846
  ]
 }
}
```