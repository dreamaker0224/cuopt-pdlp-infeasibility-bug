import pandas as pd
import numpy as np

def export_to_mps(returns_df, window_size=1200, filename="reproduce_bug.mps"):
    """
    將 Omega Ratio 優化問題導出為 MPS 格式，用於測試求解器數值問題。
    """
    # 數據準備
    returns_window = returns_df.iloc[:window_size]
    avg_returns = returns_window.mean(axis=0).values
    returns_array = returns_window.values
    T, N = returns_array.shape

    # 常數
    DELTA = 0.5
    TAU = 0.001
    LOW = 0.01
    UP = 0.4
    REQUIRED_RETURN = 0.0001
    p1 = p2 = 0.0025

    with open(filename, 'w') as f:
        f.write(f"NAME          OMEGA_REPRO\n")
        
        # 1. OBJSENSE (部分求解器支持，若不支持則默認最小化，我們在後面處理符號)
        f.write("OBJSENSE\n    MAXIMIZE\n")

        # 2. ROWS
        f.write("ROWS\n")
        f.write(" N  OBJ\n")
        f.write(" E  BUDGET\n")
        f.write(" G  MINRET\n")
        for i in range(N):
            f.write(f" G  LOW_{i:04d}\n")
            f.write(f" L  UP_{i:04d}\n")
        for t in range(T):
            f.write(f" G  DOWN_{t:04d}\n")
        f.write(" G  OMEGA\n")

        # 3. COLUMNS
        f.write("COLUMNS\n")
        
        # 標記整數變量開始 (z_i)
        f.write("    MARK0000  'MARKER'                 'INTORG'\n")
        for i in range(N):
            f.write(f"    z_{i:04d}   LOW_{i:04d}  {-LOW:<10.8f}  UP_{i:04d}   {-UP:<10.8f}\n")
        f.write("    MARK0001  'MARKER'                 'INTEND'\n")

        # 權重變量 w_i
        for i in range(N):
            f.write(f"    w_{i:04d}   BUDGET    1.0         MINRET    {avg_returns[i]:<10.8f}\n")
            f.write(f"    w_{i:04d}   LOW_{i:04d}  1.0         UP_{i:04d}   1.0\n")
            f.write(f"    w_{i:04d}   OMEGA     {DELTA * avg_returns[i]:<10.8f}\n")
            for t in range(T):
                f.write(f"    w_{i:04d}   DOWN_{t:04d}  {returns_array[t, i]:<10.8f}\n")

        # 交易成本變量 l_p, l_m
        for i in range(N):
            f.write(f"    lp_{i:04d}  OBJ       {-p1:<10.8f}  BUDGET    {p1:<10.8f}\n")
            f.write(f"    lm_{i:04d}  OBJ       {-p2:<10.8f}  BUDGET    {-p2:<10.8f}\n")

        # 下行風險變量 ita_t
        ita_coeff = -(1 - DELTA) / T
        for t in range(T):
            f.write(f"    ita_{t:04d} DOWN_{t:04d}  1.0         OMEGA     {ita_coeff:<10.8f}\n")

        # 輔助變量 psi
        f.write(f"    psi       OBJ       1.0         OMEGA     -1.0\n")

        # 4. RHS
        f.write("RHS\n")
        f.write(f"    RHS1      BUDGET    1.0         MINRET    {REQUIRED_RETURN:<10.8f}\n")
        for t in range(T):
            f.write(f"    RHS1      DOWN_{t:04d}  {TAU:<10.8f}\n")
        f.write(f"    RHS1      OMEGA     {DELTA * TAU:<10.8f}\n")

        # 5. BOUNDS (w, l_p, l_m 都有 UP 限制)
        f.write("BOUNDS\n")
        for i in range(N):
            f.write(f" UP BND1      w_{i:04d}   {UP}\n")
            f.write(f" UP BND1      lp_{i:04d}  {UP}\n")
            f.write(f" UP BND1      lm_{i:04d}  {UP}\n")
            f.write(f" BV BND1      z_{i:04d}\n")
        f.write(" FR BND1      psi\n") # psi 是無限制變量

        f.write("ENDATA\n")

    print(f"MPS file generated: {filename}")

df = pd.read_csv('us_stocks_30y_daily_returns.csv', index_col=0)
export_to_mps(df)