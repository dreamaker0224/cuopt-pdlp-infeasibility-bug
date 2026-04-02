#!/usr/bin/env python3
"""
Minimal Reproducible Example for cuOpt PDLP "Infeasible" Bug

Bug: cuOpt PDLP reports "MIP Infeasible" for Omega Ratio portfolio optimization
     with 1200-period window, but Gurobi finds feasible solution.

Issue: False infeasibility declaration due to numerical issues with coefficient
       range [6e-07, 1e+00] spanning 7 orders of magnitude.
"""

import os
from cuopt.linear_programming.problem import Problem, INTEGER, CONTINUOUS, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings, SolverMethod, PDLPSolverMode
from cuopt.linear_programming.solver.solver_parameters import CUOPT_METHOD, CUOPT_PDLP_SOLVER_MODE
import pandas as pd
import numpy as np
import time

# Model parameters
DELTA = 0.5
TAU = 0.001
LOW = 0.01
UP = 0.4
REQUIRED_RETURN = 0.0001
p_1 = p_2 = 0.0025  # Transaction costs

def solve_omega_cuopt(returns_df, window_size=1200):
    """
    Solve Omega Ratio Portfolio Optimization using cuOpt PDLP

    Args:
        returns_df: DataFrame of stock returns (periods × stocks)
        window_size: Number of periods to use (default 1200)

    Returns:
        dict: Results including status, objective, solve time
    """
    print(f"{'='*80}")
    print(f"Omega Ratio Portfolio Optimization - cuOpt PDLP")
    print(f"Window: {window_size} periods")
    print(f"{'='*80}\n")

    # Extract window data
    returns_window = returns_df.iloc[:window_size]
    avg_returns = returns_window.mean(axis=0).values
    returns_array = returns_window.values
    T, N = returns_array.shape

    print(f"Problem Size:")
    print(f"  Stocks (N): {N}")
    print(f"  Periods (T): {T}")
    print(f"  Variables: {N*4 + T + 1} ({N} integer)")
    print(f"  Constraints: {2 + N*2 + T + 1}\n")

    # Create model
    problem = Problem(f"Omega_LongOnly_1200d")

    # Variables
    w = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'w_{i}') for i in range(N)]
    l_p = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'l_p_{i}') for i in range(N)]
    l_m = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'l_m_{i}') for i in range(N)]
    z = [problem.addVariable(vtype=INTEGER, lb=0, ub=1, name=f'z_{i}') for i in range(N)]
    ita = [problem.addVariable(vtype=CONTINUOUS, lb=0, name=f'ita_{t}') for t in range(T)]
    psi = problem.addVariable(vtype=CONTINUOUS, name='psi')

    # Objective: Maximize Ω - transaction costs
    problem.setObjective(
        psi - sum((p_1 * l_p[i] + p_2 * l_m[i]) for i in range(N)),
        sense=MAXIMIZE
    )

    # Constraints
    # 1. Budget constraint
    problem.addConstraint(
        sum((w[i] + p_1 * l_p[i] - p_2 * l_m[i]) for i in range(N)) == 1,
        name='budget'
    )

    # 2. Minimum return
    problem.addConstraint(
        sum(avg_returns[i] * w[i] for i in range(N)) >= REQUIRED_RETURN,
        name='min_return'
    )

    # 3. Buy-in thresholds (long-only)
    for i in range(N):
        problem.addConstraint(w[i] >= LOW * z[i], name=f'buy_in_lower_{i}')
        problem.addConstraint(w[i] <= UP * z[i], name=f'buy_in_upper_{i}')

    # 4. Downside constraints (creates coefficient range issue)
    for t in range(T):
        port_return_t = sum(returns_array[t, i] * w[i] for i in range(N))
        problem.addConstraint(ita[t] + port_return_t >= TAU, name=f'downside_{t}')

    # 5. Omega constraint
    avg_port_return = sum(avg_returns[i] * w[i] for i in range(N))
    problem.addConstraint(
        DELTA * (avg_port_return - TAU) - (1 - DELTA) / T * sum(ita[t] for t in range(T)) >= psi,
        name='omega'
    )

    # Solver settings
    settings = SolverSettings()
    # Use concurrent mode (default, equivalent to cuopt_cli default behavior)
    # settings.set_parameter(CUOPT_METHOD, SolverMethod.PDLP)
    # settings.set_parameter(CUOPT_PDLP_SOLVER_MODE, PDLPSolverMode.Stable2)
    settings.set_parameter("time_limit", 60)  # 1 minute
    settings.set_parameter("num_cpu_threads", 19)

    # Solve
    print("Solving...\n")
    start_time = time.time()
    problem.solve(settings)
    solve_time = time.time() - start_time

    # Results
    status = problem.Status.name
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Status: {status}")
    print(f"Solve Time: {solve_time:.2f}s")

    result = {
        'status': status,
        'solve_time': solve_time,
        'window_size': window_size,
        'stocks': N,
        'periods': T
    }

    if status in ["Optimal", "FeasibleFound", "TimeLimit"]:
        try:
            w_vals = np.array([w[i].getValue() for i in range(N)])
            if not np.any(np.isnan(w_vals)) and np.sum(w_vals) > 1e-6:
                omega = problem.ObjValue
                port_return = np.sum(avg_returns * w_vals)
                num_assets = int(np.sum(w_vals > 1e-6))

                print(f"Objective (Ω): {omega:.8f}")
                print(f"Portfolio Return: {port_return:.6f}")
                print(f"Number of Assets: {num_assets}")

                result.update({
                    'objective': float(omega),
                    'portfolio_return': float(port_return),
                    'num_assets': num_assets,
                    'success': True
                })
            else:
                print("No feasible solution found")
                result['success'] = False
        except Exception as e:
            print(f"Error extracting solution: {e}")
            result['success'] = False
    else:
        print("❌ Problem declared INFEASIBLE (this is the bug!)")
        result['success'] = False

    print(f"{'='*80}\n")

    return result

if __name__ == "__main__":
    import sys

    # Load data
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = 'nvidia_issue_mre/synthetic_russell3000_30y_daily.csv'

    print(f"Loading data: {data_file}")
    df = pd.read_csv(data_file, index_col=0, parse_dates=True)
    print(f"Data shape: {df.shape[0]} periods × {df.shape[1]} stocks\n")

    # Run with 1200-period window (triggers bug)
    result = solve_omega_cuopt(df, window_size=1200)

    # Expected: Should find feasible solution (as Gurobi does)
    # Actual: cuOpt PDLP reports "Infeasible"
    if result['status'] == 'Infeasible':
        print("\n⚠️  BUG REPRODUCED: cuOpt PDLP incorrectly reports 'Infeasible'")
        print("    Gurobi finds feasible solution for the same problem!")
        sys.exit(1)
    else:
        print("\n✓ Problem solved successfully")
        sys.exit(0)
