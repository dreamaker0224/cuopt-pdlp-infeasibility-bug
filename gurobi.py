#!/usr/bin/env python3
"""
Omega Ratio Portfolio Optimization - Long Only (Gurobi)
滑動窗口測試 - 參照 Russell 3000 數據

Model:
    Maximize: Ω = ψ - transaction_costs

    Subject to:
    - Σ (w_i + p_1*l_p_i - p_2*l_m_i) = 1 (budget with turnover)
    - Σ μ_i w_i >= R_min (minimum return)
    - L * z_i <= w_i <= U * z_i (buy-in thresholds)
    - ita_t + Σ r_ti w_i >= τ, ∀t (downside constraint)
    - δ(Σ μ_i w_i - τ) - (1-δ)/T Σ ita_t >= ψ (omega constraint)
    - z_i ∈ {0,1}, w_i >= 0, ita_t >= 0, l_p_i >= 0, l_m_i >= 0

Parameters: δ=0.5, τ=0.001, L=0.01, U=0.4, R_min=0.0001
Transaction costs: p_1=0.0025, p_2=0.0025
"""

import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import numpy as np
import time
import sys
import os
from datetime import datetime
from pathlib import Path

# Window sizes (same as MAD model)
WINDOW_SIZES = {
    '60d': 60,
    '120d': 120,
    '240d': 240,
    '600d': 600,
    '480d': 480,
    '1200d': 1200,
}

# Model parameters
DELTA = 0.5
TAU = 0.001
LOW = 0.01
UP = 0.4
REQUIRED_RETURN = 0.0001  # 0.01% minimum return (同 CVaR 和 MAD)
TIME_LIMIT = 60  # 1 minute (for testing purposes)
NUM_THREADS = 19
p_1 = 0.0025  # Transaction cost per unit of turnover
p_2 = 0.0025  # Transaction cost per unit of turnover

DATA_FILE = 'datasets/russell3000/us_stocks_30y_daily_returns.csv'

def load_data():
    """Load Russell 3000 daily returns data"""
    print(f"載入數據: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE, index_col=0, parse_dates=True)
    print(f"數據形狀: {df.shape} ({df.shape[0]} 期 × {df.shape[1]} 股票)")
    return df

def solve_omega_period(period_idx, returns_window, stock_names):
    """
    Solve Omega ratio optimization for a single period (Long-Only)

    Args:
        period_idx: Period index
        returns_window: DataFrame of returns for the window
        stock_names: List of stock names

    Returns:
        dict: Results including weights, objective value, solve time
    """
    start_time = time.time()

    # Data preparation
    avg_returns = returns_window.mean(axis=0).values
    returns_array = returns_window.values
    T, N = returns_array.shape

    # Create model
    model_build_start = time.time()
    model = gp.Model(f"Omega_LongOnly_period_{period_idx}")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', TIME_LIMIT)
    model.setParam('Threads', NUM_THREADS)
    model.setParam('MIPGap', 1e-4)

    # Decision variables (Long-Only with transaction costs)
    w = model.addVars(N, lb=0, ub=UP, vtype=GRB.CONTINUOUS, name='w')
    l_p = model.addVars(N, lb=0, ub=UP, vtype=GRB.CONTINUOUS, name='l_p')  # Turnover up
    l_m = model.addVars(N, lb=0, ub=UP, vtype=GRB.CONTINUOUS, name='l_m')  # Turnover down
    z = model.addVars(N, vtype=GRB.BINARY, name='z')
    ita = model.addVars(T, lb=0, vtype=GRB.CONTINUOUS, name='ita')
    psi = model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name='psi')

    build_time = time.time() - model_build_start

    # Objective: Maximize Omega - transaction costs
    model.setObjective(psi - gp.quicksum((p_1 * l_p[i] + p_2 * l_m[i]) for i in range(N)), GRB.MAXIMIZE)

    # Constraints
    # 1. Budget constraint (with transaction costs)
    model.addConstr(
        gp.quicksum((w[i] + p_1 * l_p[i] - p_2 * l_m[i]) for i in range(N)) == 1,
        name='budget'
    )

    # 2. Minimum return constraint
    model.addConstr(
        gp.quicksum(avg_returns[i] * w[i] for i in range(N)) >= REQUIRED_RETURN,
        name='min_return'
    )

    # 3. Buy-in thresholds (Long-Only)
    for i in range(N):
        model.addConstr(w[i] >= LOW * z[i], name=f'buy_in_lower_{i}')
        model.addConstr(w[i] <= UP * z[i], name=f'buy_in_upper_{i}')

    # 4. Downside constraints for each scenario
    for t in range(T):
        port_return_t = gp.quicksum(returns_array[t, i] * w[i] for i in range(N))
        model.addConstr(ita[t] + port_return_t >= TAU, name=f'downside_{t}')

    # 5. Omega constraint
    avg_port_return = gp.quicksum(avg_returns[i] * w[i] for i in range(N))
    model.addConstr(
        DELTA * (avg_port_return - TAU) - (1 - DELTA) / T * gp.quicksum(ita[t] for t in range(T)) >= psi,
        name='omega'
    )

    # Solve
    model_update_start = time.time()
    model.update()
    model_update_time = time.time() - model_update_start

    solve_start = time.time()
    model.optimize()
    solve_time = time.time() - solve_start
    total_time = time.time() - start_time

    # Extract results
    status_map = {
        GRB.OPTIMAL: 'Optimal',
        GRB.TIME_LIMIT: 'TimeLimit',
        GRB.INFEASIBLE: 'Infeasible',
        GRB.UNBOUNDED: 'Unbounded'
    }
    status = status_map.get(model.status, f'Status_{model.status}')

    result = {
        'period': period_idx,
        'status': status,
        'solve_time': solve_time,
        'build_time': build_time,
        'total_time': total_time,
        'variables': model.NumVars,
        'constraints': model.NumConstrs,
        'periods': T,
        'stocks': N
    }

    if model.status in [GRB.OPTIMAL, GRB.TIME_LIMIT] and model.SolCount > 0:
        try:
            w_vals = np.array([w[i].X for i in range(N)])

            # Check if we have a valid feasible solution
            # (TimeLimit might not have found any feasible solution)
            has_solution = not np.any(np.isnan(w_vals)) and np.sum(w_vals) > 1e-6

            if not has_solution:
                # TimeLimit but no feasible solution found
                result['status'] = 'TimeLimit_NoFeasible' if status == 'TimeLimit' else status
                result['has_solution'] = False
                return result

            omega_value = model.objVal
            num_assets = int(np.sum(w_vals > 1e-6))
            max_weight = float(np.max(w_vals)) if N > 0 else 0
            portfolio_return = np.sum(avg_returns * w_vals)

            mip_gap = model.MIPGap if hasattr(model, 'MIPGap') else None
            node_count = model.NodeCount if hasattr(model, 'NodeCount') else None

            result.update({
                'objective': float(omega_value),
                'omega': float(omega_value),
                'num_assets': num_assets,
                'max_weight': max_weight,
                'portfolio_return': float(portfolio_return),
                'mip_gap': float(mip_gap) if mip_gap is not None else None,
                'node_count': int(node_count) if node_count is not None else None,
                'weights': w_vals,
                'has_solution': True
            })
        except Exception as e:
            result['error'] = str(e)
            result['has_solution'] = False

    return result

def run_optimization(window_name, window_size, output_dir=None):
    """Run Omega long-only optimization for single period test"""

    # Create output directory (use absolute path based on script location)
    if output_dir is None:
        script_dir = Path(__file__).resolve().parent
        output_dir = script_dir.parent.parent.parent / 'results' / 'omega_longonly' / 'gurobi'

    os.makedirs(output_dir, exist_ok=True)

    # Open output file for logging all output
    output_file = Path(output_dir) / f"omega_longonly_gurobi_{window_name}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        # Tee-like class to write to both file and stdout/stderr
        class Tee:
            def __init__(self, file, console):
                self.file = file
                self.console = console

            def write(self, message):
                self.file.write(message)
                self.file.flush()
                self.console.write(message)
                self.console.flush()

            def flush(self):
                self.file.flush()
                self.console.flush()

        # Redirect stdout and stderr to both file and console
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = Tee(f, original_stdout)
        sys.stderr = Tee(f, original_stderr)

        try:
            print("=" * 80)
            print(f"  Omega Ratio Portfolio Optimization (Long-Only) - Gurobi")
            print(f"  Window: {window_name} ({window_size} periods)")
            print("=" * 80)
            print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Load data
            df = load_data()
            stock_names = df.columns.tolist()
            N = len(stock_names)
            M = len(df)

            print(f"\n模型參數:")
            print(f"  股票數: {N}")
            print(f"  買入範圍: [{LOW}, {UP}]")
            print(f"  最低回報: {REQUIRED_RETURN}")
            print(f"  時間限制: {TIME_LIMIT}s")
            print(f"  執行緒: {NUM_THREADS}")
            print(f"  交易成本: p_1={p_1}, p_2={p_2}")
            print()

            # Test single period (period 0)
            print(f"測試單期 (period 0)...")
            print()

            returns_window = df.iloc[0:window_size]

            try:
                result = solve_omega_period(0, returns_window, stock_names)

                # Print results
                print("=" * 80)
                print("結果")
                print("=" * 80)

                status = result['status']
                solve_time = result['solve_time']

                print(f"狀態: {status}")
                print(f"求解時間: {solve_time:.2f}s")
                print(f"建模時間: {result['build_time']:.2f}s")
                print(f"變數: {result['variables']} (整數: {result['stocks']})")
                print(f"約束: {result['constraints']}")

                # Check if solution found
                has_solution = result.get('has_solution', 'omega' in result)
                if not has_solution:
                    print(f"\n⚠️ 未找到可行解 (達時限)")
                elif 'omega' in result:
                    print(f"\n✓ 找到可行解")
                    print(f"Omega: {result['omega']:.8f}")
                    print(f"回報率: {result['portfolio_return']:.6f}")
                    print(f"資產數: {result['num_assets']}")
                    print(f"最大權重: {result['max_weight']:.4f}")

                    if result.get('mip_gap') is not None:
                        print(f"MIP Gap: {result['mip_gap']*100:.4f}%")
                    if result.get('node_count') is not None:
                        print(f"節點數: {result['node_count']}")

                if 'error' in result:
                    print(f"\n⚠️ 錯誤: {result['error']}")

            except Exception as e:
                print(f"✗ 測試失敗: {e}")
                result = {
                    'status': 'Error',
                    'error': str(e)
                }

            print()
            print(f"完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

        finally:
            # Restore stdout and stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python omega_longonly_gurobi.py <window_name>")
        print(f"  window_name: {list(WINDOW_SIZES.keys())}")
        sys.exit(1)

    window_name = sys.argv[1]

    if window_name not in WINDOW_SIZES:
        print(f"Invalid window name: {window_name}")
        print(f"Valid options: {list(WINDOW_SIZES.keys())}")
        sys.exit(1)

    window_size = WINDOW_SIZES[window_name]

    result = run_optimization(window_name, window_size)

    return result

if __name__ == "__main__":
    main()
