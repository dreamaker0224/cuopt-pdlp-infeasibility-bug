# cuOpt PDLP Reports "MIP Infeasible" but Feasible Solution Exists

## Environment
- **cuOpt Version**: 26.2.0 (git hash: f73da24d)
- **CUDA Version**: 13.1
- **GPU**: NVIDIA GeForce RTX 5060 Ti (16GB VRAM)
- **CPU**: AMD Ryzen 9 9900X 12-Core (20 threads)
- **OS**: Linux
- **Solver Method**: PDLP (Stable2 mode)
- **Python Version**: 3.x

## Problem Description

cuOpt PDLP solver incorrectly reports "MIP Infeasible" for an Omega Ratio portfolio optimization problem that **definitely has feasible solutions**.

### Expected Behavior
The problem should find a feasible or optimal solution, as:
1. The mathematical model is well-formed and has been validated
2. Similar problems with smaller window sizes (60d, 120d, 240d, 600d) solve successfully
3. **VERIFIED**: Gurobi finds a feasible solution for the **exact same problem instance**

### Actual Behavior (cuOpt PDLP)
- **Root LP Status**: INFEASIBLE
- **Final Status**: MIP Infeasible
- **Solve Time**: 1800.79s (hit time limit)
- **Root LP Infeasibility**: Primal infeasibility = 2.041834e+02 after 4507 dual simplex iterations

### Comparison: Gurobi Successfully Solves the Same Problem

**Gurobi Result (same 1200d window, same data, same constraints)**:
- **Status**: TimeLimit (but with feasible solution found)
- **Solve Time**: 1800.05s
- **Objective Value**: -0.00051630
- **Portfolio Return**: 0.001539
- **Number of Assets**: 63
- **Max Weight**: 0.0469
- **MIP Gap**: 1.2113%
- **Nodes Explored**: 160,432

**Key Point**: Gurobi proves this problem is feasible and provides a solution with 1.21% optimality gap. cuOpt incorrectly declares it infeasible.

## Problem Characteristics

### Problem Size
```
Constraints: 4,557
Variables: 7,909 (1,677 integers, 6,232 continuous)
Nonzeros: 2,029,894
```

### Coefficient Ranges (Warning Issued)
```
Objective coefficients:          [3e-03, 1e+00]
Constraint matrix coefficients:  [6e-07, 1e+00]  ⚠️ Large range (7 orders of magnitude)
Constraint RHS/bounds:           [0e+00, 1e+00]
Variable bounds:                 [0e+00, 1e+00]
```

**cuOpt Warning**: "input problem contains a large range of coefficients: consider reformulating to avoid numerical difficulties"

### Presolver Results
```
Before presolve: 4,557 constraints, 7,909 variables, 1,034,918 nonzeros
After presolve:  4,557 constraints, 7,908 variables, 1,034,917 nonzeros
Papilo removed: 0 constraints, 1 variable, 994,977 nonzeros
```

## Model Formulation

**Omega Ratio Portfolio Optimization (Long-Only)**

### Decision Variables
- `w[i]` (continuous): Portfolio weight for stock i, bounds [0, 0.4]
- `z[i]` (binary): Buy-in indicator for stock i
- `l_p[i]` (continuous): Positive turnover, bounds [0, 0.4]
- `l_m[i]` (continuous): Negative turnover, bounds [0, 0.4]
- `ita[t]` (continuous): Downside deviation at time t, bounds [0, ∞)
- `psi` (continuous): Omega ratio surrogate variable

### Objective
```
Maximize: psi - Σ(p_1 * l_p[i] + p_2 * l_m[i])
where: p_1 = p_2 = 0.0025
```

### Constraints
1. **Budget**: `Σ(w[i] + p_1*l_p[i] - p_2*l_m[i]) = 1`
2. **Minimum Return**: `Σ(μ[i] * w[i]) >= 0.0001`
3. **Buy-in Lower**: `w[i] >= 0.01 * z[i]` for all i
4. **Buy-in Upper**: `w[i] <= 0.4 * z[i]` for all i
5. **Downside** (T=1200): `ita[t] + Σ(r[t,i] * w[i]) >= 0.001` for all t
6. **Omega**: `δ*(Σ(μ[i]*w[i]) - τ) - (1-δ)/T*Σ(ita[t]) >= psi`
   - where: δ=0.5, τ=0.001

### Data Characteristics
- **Returns Matrix**: 1200 periods × 1677 stocks (Russell 3000 subset)
- **Return Range**: Typical daily returns in [-0.1, 0.1]
- **Mean Returns (μ)**: Computed from 1200-day historical window

## Solver Configuration

```python
settings = SolverSettings()
settings.set_parameter(CUOPT_METHOD, SolverMethod.PDLP)
settings.set_parameter(CUOPT_PDLP_SOLVER_MODE, PDLPSolverMode.Stable2)
settings.set_parameter("time_limit", 1800)
settings.set_parameter("num_cpu_threads", 19)
```

## Reproduction

### Complete Solver Log
```
Setting parameter method to 1
Setting parameter pdlp_solver_mode to 1
Setting parameter time_limit to 1.800000e+03
Setting parameter num_cpu_threads to 19

Solving a problem with 4557 constraints, 7909 variables (1677 integers), and 2029894 nonzeros
Problem scaling:
Objective coefficents range:          [3e-03, 1e+00]
Constraint matrix coefficients range: [6e-07, 1e+00]
Constraint rhs / bounds range:        [0e+00, 1e+00]
Variable bounds range:                [0e+00, 1e+00]
Warning: input problem contains a large range of coefficients: consider reformulating to avoid numerical difficulties.

Original problem: 4557 constraints, 7909 variables, 1034918 nonzeros
Calling Papilo presolver (git hash 741a2b9c)
Presolve status: reduced the problem
Presolve removed: 0 constraints, 1 variables, 994977 nonzeros
Presolved problem: 4557 constraints, 7908 variables, 1034917 nonzeros
Papilo presolve time: 0.41
Objective offset 0.000500 scaling_factor -1.000000
Model fingerprint: 0x27d28143
Running presolve!
After cuOpt presolve: 4557 constraints, 7908 variables, objective offset 0.000500.
cuOpt presolve time: 2.66

Solving LP root relaxation in concurrent mode
Skipping column scaling
Dual Simplex Phase 1
Dual feasible solution found.
Dual Simplex Phase 2
 Iter     Objective           Num Inf.  Sum Inf.     Perturb  Time
    0 +1.7187346666666681e-01    1421 1.43669609e+05 0.00e+00 3.24
    1 +1.7143934166666683e-01     592 1.62134800e+00 0.00e+00 3.24
 1000 +1.6935419478269423e-01     650 6.38744096e+00 1.00e-07 3.54
 2000 +1.6970292132262182e-01    1017 3.17878878e+07 0.00e+00 4.07
 3000 -1.5915749266835666e+00     264 4.49723512e+05 0.00e+00 5.46
 4000 -1.6631818201158506e+00     121 1.46871161e+05 0.00e+00 6.66
No entering variable found. Iter 4507
Scaled infeasibility 1.226897e-08
Dual infeasibility after removing perturbation 0.000000e+00
Removed perturbation of 1.17e-04.
Updated primal infeasibility: 2.041834e+02
Continuing with perturbation removed and steepest edge norms reset
No entering variable found. Iter 4507
Scaled infeasibility 1.226897e-08
Dual infeasibility 0.000000e+00
Primal infeasibility 2.041834e+02
Updates 19
Steepest edge 1.226897e-08


Root relaxation returned: INFEASIBLE


MIP Infeasible
```

### Minimal Reproducible Example (MRE)

A complete MRE is provided in the `nvidia_issue_mre/` directory:

**Files**:
1. `generate_synthetic_data.py` - Generate synthetic market data (avoids proprietary data issues)
2. `omega_cuopt_bug_mre.py` - Minimal script to reproduce the bug
3. `README.md` - Detailed reproduction instructions

**Quick Start**:
```bash
# Generate synthetic data
python nvidia_issue_mre/generate_synthetic_data.py

# Reproduce bug
python nvidia_issue_mre/omega_cuopt_bug_mre.py
```

Expected output: cuOpt reports "Infeasible" (incorrect)

**Note**: We use synthetic data with similar statistical properties to real financial data to protect proprietary information while still reproducing the bug.

## Secondary Issue: Wasteful Execution After Root LP Failure

After PDLP declares the root LP infeasible, cuOpt continues executing silently for the full time limit, wasting computational resources.

### Observed Behavior (cuOpt 26.2.0 with 60s time limit):

```
Dual Simplex Phase 2: 3150 iterations
Time at Root LP failure: ~9 seconds

Root relaxation returned: INFEASIBLE
MIP Infeasible

[Silent execution continues...]

Final Status: Infeasible
Total Solve Time: 63.17 seconds
```

**Analysis**:
- Root LP fails at ~9 seconds
- Solver continues silently for ~54 seconds (no output, no progress)
- Total time: 63 seconds (slightly exceeds 60s time limit)
- No Branch & Bound nodes logged or visible progress

### Expected Behavior:

When the root LP relaxation is proven infeasible, the entire MIP is provably infeasible. The solver should:
1. Immediately terminate after root LP failure
2. Not waste ~54 seconds on silent execution
3. Respect the time limit more strictly

### Version Comparison:

| cuOpt Version | Root LP Fail Time | Total Solve Time | Silent Execution | User Message |
|---------------|-------------------|------------------|------------------|--------------|
| **26.2.0** (latest) | ~9s | 63s | 54s (86% of time) | None |
| **25.10.1** | ~1s | 60s | 59s (98% of time) | "Problem is primal infeasible, continuing anyway!" |

**Notes**:
- Version 26.2.0 removed the "continuing anyway!" message but kept the wasteful behavior
- Both versions continue execution after declaring infeasibility
- This wastes significant GPU/CPU resources on problems that are already determined to be infeasible

## Questions for NVIDIA Team

1. **Is this a numerical stability issue?**
   - The coefficient range warning (6e-07 to 1e+00) spans 7 orders of magnitude
   - Could PDLP's finite precision arithmetic cause false infeasibility?

2. **Why did dual simplex converge to primal infeasibility = 204.18?**
   - Dual infeasibility: 0 (dual feasible)
   - Primal infeasibility: 2.041834e+02 (large violation)
   - Does this indicate numerical issues or actual infeasibility?

3. **Should I try different solver settings?**
   - Would switching from `PDLPSolverMode.Stable2` to another mode help?
   - Are there tighter tolerance parameters I should set?
   - Would increasing time limit allow the solver to find feasibility?

4. **Recommended reformulation strategies?**
   - Should I scale the constraint matrix coefficients?
   - Should I rescale the return data to avoid small coefficients (6e-07)?
   - Would splitting large constraints improve numerical stability?

5. **Is this a known limitation of PDLP for portfolio optimization?**
   - Should I consider using a different cuOpt solver method for this problem class?
   - Are there known issues with PDLP handling mixed-integer portfolio problems?

6. **Why does cuOpt continue execution after root LP infeasibility?**
   - Root LP infeasible should imply MIP infeasible (no need to continue)
   - Is the silent 54-second execution doing useful work or is it a bug?
   - Can this wasteful behavior be disabled?

## Additional Context

- **Smaller windows succeed**: Same formulation with 60d, 120d, 240d, 600d windows all solve to optimality
- **Scaling hypothesis**: Larger window (1200 periods) creates more downside constraints (1200 vs 600), potentially exacerbating numerical issues
- **Gurobi comparison**:
  - Same problem instance, same time limit (1800s)
  - Gurobi finds feasible solution with objective -0.00051630
  - Gurobi explores 160,432 nodes before hitting time limit
  - MIP gap at termination: 1.21%
  - **This proves the problem is feasible**, cuOpt's "Infeasible" status is incorrect

## Attachments

- **cuOpt log**: `results/omega_longonly/cuopt/logs/omega_longonly_cuopt_1200d_20260324_113717.log`
- **Gurobi log (proof of feasibility)**: `results/omega_longonly/gurobi/logs/omega_longonly_gurobi_1200d_20260324_121304.log`
- **Python script**: `script/omega/cuopt/omega_longonly_cuopt.py`
- **Data file**: Available upon request (proprietary financial data)

## Request

Based on the evidence that Gurobi successfully finds a feasible solution for the same problem instance, this appears to be **two related bugs in cuOpt PDLP**:

### Bug 1: False Infeasibility (Primary Issue)
cuOpt PDLP incorrectly reports "MIP Infeasible" due to numerical instability in the root LP, even though the problem has feasible solutions (proven by Gurobi).

### Bug 2: Wasteful Execution (Secondary Issue)
After declaring root LP infeasible, cuOpt continues silently executing for ~54 seconds (86% of solve time), wasting computational resources on a problem already determined to be infeasible.

We would appreciate:
1. **Bug confirmation**: Are these known issues with PDLP numerical stability and termination logic?
2. **Workaround**: Recommended solver settings or problem reformulation to avoid false infeasibility
3. **Fix timeline**: When can we expect patches for these issues?
4. **Alternative solver**: Should we use a different cuOpt method (not PDLP) for this problem class?

**Impact**:
- False infeasibility prevents us from using cuOpt on large-scale portfolio optimization problems (1200+ time periods)
- Wasteful execution multiplies computational cost when problems incorrectly fail
- Combined issues significantly limit cuOpt's applicability in financial optimization use cases

Thank you for your support!

---
**Report Date**: 2026-03-29
**Contact**: [Your email/GitHub handle]
**Project**: test-cuopt-portfolio (GPU vs CPU MILP solver comparison)
