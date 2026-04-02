#!/usr/bin/env python3
"""
使用 cuOpt Python API 官方的 writeMPS() 方法導出 MPS 檔案
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

from cuopt.linear_programming.problem import Problem, INTEGER, CONTINUOUS, MAXIMIZE
import pandas as pd
import numpy as np

# Model parameters
DELTA = 0.5
TAU = 0.001
LOW = 0.01
UP = 0.4
REQUIRED_RETURN = 0.0001
p_1 = p_2 = 0.0025

# Load data
df = pd.read_csv('us_stocks_30y_daily_returns.csv', index_col=0)
returns_window = df.iloc[:1200]
avg_returns = returns_window.mean(axis=0).values
returns_array = returns_window.values
T, N = returns_array.shape

print(f"建構問題: T={T}, N={N}")

# Create problem
problem = Problem("Omega_LongOnly_1200d")

# Variables
w = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'w_{i}') for i in range(N)]
l_p = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'l_p_{i}') for i in range(N)]
l_m = [problem.addVariable(vtype=CONTINUOUS, lb=0, ub=UP, name=f'l_m_{i}') for i in range(N)]
z = [problem.addVariable(vtype=INTEGER, lb=0, ub=1, name=f'z_{i}') for i in range(N)]
ita = [problem.addVariable(vtype=CONTINUOUS, lb=0, name=f'ita_{t}') for t in range(T)]
psi = problem.addVariable(vtype=CONTINUOUS, name='psi')

# Objective
problem.setObjective(
    psi - sum((p_1 * l_p[i] + p_2 * l_m[i]) for i in range(N)),
    sense=MAXIMIZE
)

# Constraints
problem.addConstraint(
    sum((w[i] + p_1 * l_p[i] - p_2 * l_m[i]) for i in range(N)) == 1,
    name='budget'
)

problem.addConstraint(
    sum(avg_returns[i] * w[i] for i in range(N)) >= REQUIRED_RETURN,
    name='min_return'
)

for i in range(N):
    problem.addConstraint(w[i] >= LOW * z[i], name=f'buy_in_lower_{i}')
    problem.addConstraint(w[i] <= UP * z[i], name=f'buy_in_upper_{i}')

for t in range(T):
    port_return_t = sum(returns_array[t, i] * w[i] for i in range(N))
    problem.addConstraint(ita[t] + port_return_t >= TAU, name=f'downside_{t}')

avg_port_return = sum(avg_returns[i] * w[i] for i in range(N))
problem.addConstraint(
    DELTA * (avg_port_return - TAU) - (1 - DELTA) / T * sum(ita[t] for t in range(T)) >= psi,
    name='omega'
)

# 使用官方的 writeMPS() 方法導出
output_file = "python_api_exported.mps"
print(f"\n使用官方 writeMPS() 方法導出: {output_file}")
problem.writeMPS(output_file)
print(f"✅ 已導出: {output_file}")
