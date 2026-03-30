#!/usr/bin/env python3
"""
Generate synthetic portfolio returns data for cuOpt bug reproduction
模擬與真實 Russell 3000 數據相似的合成收益率數據
"""

import pandas as pd
import numpy as np

def generate_synthetic_returns(n_periods=7547, n_stocks=1677, seed=42):
    """
    Generate synthetic daily returns with characteristics similar to real market data

    Args:
        n_periods: Number of time periods (7547 for 30 years daily)
        n_stocks: Number of stocks (1677 for Russell 3000 subset)
        seed: Random seed for reproducibility

    Returns:
        DataFrame with synthetic returns
    """
    np.random.seed(seed)

    print(f"生成合成數據: {n_periods} 期 × {n_stocks} 股票")

    # 基礎收益率：接近真實市場統計特徵
    # 日收益率均值 ~0.0003 (約年化 7.5%)，標準差 ~1.5%
    base_returns = np.random.normal(0.0003, 0.015, (n_periods, n_stocks))

    # 加入市場因子（所有股票有相關性）
    market_factor = np.random.normal(0, 0.01, n_periods).reshape(-1, 1)
    market_beta = np.random.uniform(0.5, 1.5, n_stocks)  # beta 在 0.5-1.5 之間

    returns = base_returns + market_factor * market_beta

    # 加入極端事件（~5% 的時間）
    extreme_events = np.random.choice([0, 1], size=(n_periods, n_stocks), p=[0.95, 0.05])
    extreme_returns = np.random.normal(0, 0.05, (n_periods, n_stocks))
    returns += extreme_events * extreme_returns

    # 裁剪到合理範圍（-20% ~ +20% 日收益率）
    returns = np.clip(returns, -0.20, 0.20)

    # 建立 DataFrame
    stock_names = [f'STOCK_{i:04d}' for i in range(n_stocks)]
    dates = pd.date_range('1996-01-01', periods=n_periods, freq='D')

    df = pd.DataFrame(returns, index=dates, columns=stock_names)

    # 統計摘要
    print(f"\n數據統計:")
    print(f"  平均收益率: {df.mean().mean():.6f}")
    print(f"  標準差: {df.std().mean():.6f}")
    print(f"  最小值: {df.min().min():.6f}")
    print(f"  最大值: {df.max().max():.6f}")
    print(f"  收益率範圍: [{df.min().min():.6f}, {df.max().max():.6f}]")

    return df

if __name__ == "__main__":
    # 生成完整數據集
    df = generate_synthetic_returns(n_periods=7547, n_stocks=1677, seed=42)

    # 儲存
    output_file = 'synthetic_russell3000_30y_daily.csv'
    df.to_csv(output_file)
    print(f"\n✓ 已儲存至: {output_file}")
    print(f"  檔案大小: {df.shape[0]} 行 × {df.shape[1]} 列")
