# cuOpt PDLP False Infeasibility Bug Report

[![cuOpt Version](https://img.shields.io/badge/cuOpt-26.2.0-green.svg)](https://docs.nvidia.com/cuopt/)
[![CUDA](https://img.shields.io/badge/CUDA-13.0-blue.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Status](https://img.shields.io/badge/Status-Reproducible-red.svg)](https://github.com)

## 🐛 Bug Summary

cuOpt 26.2.0 PDLP and concurrent mode solver incorrectly reports **"MIP Infeasible"** for a portfolio optimization problem that has a **proven feasible solution** (verified with Gurobi).

## 🎯 Quick Facts

| Aspect | cuOpt PDLP | Gurobi | Verdict |
|--------|-----------|--------|---------|
| **Status** | ❌ Infeasible | ✅ Feasible | **Bug** |
| **Solve Time** | 63s | 1800s | - |
| **Objective** | N/A | -0.00051630 | cuOpt wrong |
| **Root Cause** | Numerical instability | Robust solver | - |

## 📋 Problem Details

**Type**: Omega Ratio Portfolio Optimization (MILP)
**Size**: 4,557 constraints, 7,909 variables (1,677 binary), 2M+ nonzeros
**Data**: 1,200 periods × 1,677 stocks (Russell 3000 subset)

**Coefficient Range**: [1e-08, 1e+00] ← 8 orders of magnitude causes numerical issues


### Run MRE

```bash

# Generate synthetic data 
python generate_synthetic_data.py

# Run bug reproduction 
python reproduce_bug.py
```

**Expected Output**:
```
Status: Infeasible  ← Bug: Should be feasible!
Solve Time: 63.17s
```

## 📁 Repository Contents

```
.
├── README.md                       # This file
├── reproduce_bug.py                # Main bug reproduction script (60s)
├── generate_synthetic_data.py      # Synthetic data generator
├── DETAILED_ANALYSIS.md            # Complete technical analysis
├── logs/                           # Example logs
│   ├── cuopt_26.2.0_infeasible.log # cuOpt output (bug)
│   └── gurobi_feasible.log         # Gurobi output (proof)
└── comparison/
    └── cuopt_vs_gurobi.md          # Side-by-side comparison
```

## 🔍 Root Cause Analysis

### Issue 1: False Infeasibility (Primary)

cuOpt PDLP dual simplex converges to:
- **Dual infeasibility**: 0.0 (dual feasible ✓)
- **Primal infeasibility**: 3.83e+08 (huge violation ✗)

This indicates **numerical instability**, not true infeasibility.

### Issue 2: Wasteful Execution (Secondary)

After declaring root LP infeasible, cuOpt continues:
- Root LP fails: ~9 seconds
- Silent execution: ~54 seconds (under 1 minute timelimit)
- **Waste**: After displaying MIP infeasible, cuOpt still running till timelimit

## 📊 Detailed Analysis

See [DETAILED_ANALYSIS.md](DETAILED_ANALYSIS.md) for:
- Complete solver logs (cuOpt vs Gurobi)
- Mathematical model formulation
- Numerical stability analysis
- Version comparison (26.2.0 vs 25.10.1)



## 📝 Tested Versions

- ✅ **cuOpt 26.2.0** (latest): Bug reproduced
- ✅ **cuOpt 25.10.1**: Bug reproduced (same false infeasibility)
- ✅ **Gurobi 11.x**: Finds feasible solution (proof of bug)

## 💻 Test Environment

- **OS**: Ubuntu 24.04 LTS (Linux 6.8.0-101-generic)
- **Python**: 3.12.3
- **GPU**: NVIDIA GeForce RTX 5060 Ti
- **NVIDIA Driver**: 580.126.20
- **CUDA**: 13.0

