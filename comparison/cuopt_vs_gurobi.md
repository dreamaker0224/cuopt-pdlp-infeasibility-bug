# cuOpt vs Gurobi Comparison

## Side-by-Side Results

### Problem Instance (Identical)

- **Type**: Omega Ratio Portfolio Optimization (Long-Only)
- **Window**: 1200 days
- **Stocks**: 1677 (Russell 3000 subset)
- **Variables**: 7909 (1677 binary, 6232 continuous)
- **Constraints**: 4557
- **Nonzeros**: ~2,029,894

### Solver Configuration

| Parameter | cuOpt PDLP | Gurobi |
|-----------|------------|--------|
| **Method** | PDLP (Stable2) | Dual Simplex + Branch & Bound |
| **Time Limit** | 60s (MRE) / 1800s (original) | 1800s |
| **Threads** | 19 | 19 |
| **Hardware** | GPU (RTX 5060 Ti) + CPU | CPU only |

## Results Comparison

### cuOpt 26.2.0 Result

```
Status: Infeasible ❌
Solve Time: 63.17s
Root LP Status: INFEASIBLE

Root LP Details:
  Dual infeasibility: 0.0 (dual feasible)
  Primal infeasibility: 3.825715e+08 (huge!)
  Iterations: 3150

Objective: N/A
Solution: None
```

### Gurobi 11.x Result

```
Status: TimeLimit (with feasible solution) ✅
Solve Time: 1800.05s
Root LP Status: OPTIMAL

Solution Details:
  Objective: -0.00051630
  Portfolio Return: 0.001539
  Number of Assets: 63
  Max Weight: 0.0469
  MIP Gap: 1.2113%
  Nodes Explored: 160,432
```

## Key Differences

### 1. Root LP Behavior

| Aspect | cuOpt PDLP | Gurobi |
|--------|-----------|--------|
| **Root LP Status** | INFEASIBLE | OPTIMAL |
| **Primal Feasibility** | 3.83e+08 violation | Feasible |
| **Dual Feasibility** | OK | OK |
| **Iterations** | 3150 | N/A (proprietary) |
| **Time** | ~9s | < 1s |

**Analysis**: cuOpt's dual simplex finds a dual-feasible but primal-infeasible solution, indicating numerical issues. Gurobi solves the root LP without issues.

### 2. Overall Performance

| Metric | cuOpt PDLP | Gurobi | Winner |
|--------|-----------|--------|---------|
| **Solve Time** | 63s | 1800s | cuOpt (28×) |
| **Success Rate** | 0% (failed) | 100% | Gurobi |
| **Solution Quality** | N/A | MIP Gap 1.21% | Gurobi |
| **Resource Usage** | GPU + CPU | CPU only | - |

**Note**: cuOpt's speed advantage is meaningless when it fails to find feasible solutions.

### 3. Numerical Stability

| Aspect | cuOpt PDLP | Gurobi |
|--------|-----------|--------|
| **Coefficient Range** | [1e-08, 1e+00] | Same |
| **Warning Issued** | ✅ Yes ("large range") | ❌ No |
| **Handles Wide Range** | ❌ No (fails) | ✅ Yes (succeeds) |
| **Presolve Impact** | Minimal (removed 1 var) | Unknown |

**Analysis**: Both solvers see the same coefficient range, but Gurobi handles it robustly while cuOpt PDLP fails due to numerical instability.

## Coefficient Range Analysis

### Problem Coefficients

```
Objective:               [3e-03, 1e+00]
Constraint matrix:       [1e-08, 1e+00]  ← 8 orders of magnitude
Constraint RHS/bounds:   [0e+00, 1e+00]
Variable bounds:         [0e+00, 1e+00]
```

### Why Does This Matter?

The constraint matrix has returns data like:
- Typical returns: 0.001 to 0.01 (0.1% to 1%)
- Small returns: 1e-06 to 1e-08 (rare but present)
- Constraint coefficients: Direct multipliers of returns

**cuOpt's Issue**: PDLP uses finite-precision arithmetic. When coefficients span 8 orders of magnitude:
- Small coefficients (1e-08) lose precision
- Dual simplex struggles to maintain primal feasibility
- Results in false "infeasible" verdict

**Gurobi's Robustness**: Uses adaptive precision and robust numerical techniques to handle wide ranges.

## Conclusion

### Bug Verdict: ✅ Confirmed

Gurobi's successful solve **proves** the problem is feasible. cuOpt PDLP's "Infeasible" status is a **false negative** caused by numerical instability.

### Recommendation

For portfolio optimization with:
- Large time windows (1200+ periods)
- Wide coefficient ranges (1e-08 to 1e+00)

**Avoid cuOpt PDLP** until this numerical stability issue is fixed. Consider:
1. Alternative cuOpt solver methods (if available)
2. Problem reformulation (rescaling)
3. Continue using Gurobi for reliability

---

**References**:
- cuOpt Log: `logs/cuopt_26.2.0_infeasible.log`
- Gurobi Log: `logs/gurobi_feasible.log`
- Full Analysis: `DETAILED_ANALYSIS.md`
