#!/usr/bin/env python3
"""
减脂计划分析
用法：python analysis/plan.py --target-loss 5 --days 60 [--weight 75] [--height 175] [--age 28] [--gender male]
输出：热量缺口分析 + 进度预测图
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from analysis._font import setup as _setup_font; _setup_font()

DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def latest_weight() -> float | None:
    body_dir = DATA_DIR / "body"
    files = sorted(body_dir.glob("*.csv"), reverse=True)
    for f in files:
        if f.name == "template.csv":
            continue
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            w = df.dropna(subset=["weight_kg"])["weight_kg"]
            if not w.empty:
                return float(w.iloc[-1])
        except Exception:
            pass
    return None


def mifflin_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    if gender.lower() in ("male", "m", "男"):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def estimate_activity(workout_days_per_week: float) -> float:
    """根据每周训练天数估算活动系数"""
    if workout_days_per_week < 1:
        return 1.2
    elif workout_days_per_week < 3:
        return 1.375
    elif workout_days_per_week < 5:
        return 1.55
    else:
        return 1.725


def weekly_workouts_from_data() -> float:
    workout_dir = DATA_DIR / "workouts"
    files = sorted(workout_dir.glob("*.json"), reverse=True)[:2]
    total, days_span = 0, 0
    for f in files:
        try:
            data = json.loads(f.read_text())
            total += len(data)
            days_span += 30
        except Exception:
            pass
    if days_span == 0:
        return 3
    return total / days_span * 7


def weight_trend() -> float | None:
    """用最近体重数据线性拟合，返回 kg/天 变化率"""
    body_dir = DATA_DIR / "body"
    dfs = []
    for f in sorted(body_dir.glob("*.csv")):
        if f.name == "template.csv":
            continue
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            dfs.append(df.dropna(subset=["weight_kg"]))
        except Exception:
            pass
    if not dfs:
        return None
    df = pd.concat(dfs).sort_values("date")
    if len(df) < 5:
        return None
    x = (df["date"] - df["date"].iloc[0]).dt.days.values
    y = df["weight_kg"].values
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)


def plot_projection(start_weight: float, target_loss: float, days: int,
                    daily_deficit: float, trend_kgd: float | None, tag: str):
    start = date.today()
    dates = [start + timedelta(days=i) for i in range(days + 1)]
    planned = [start_weight - (daily_deficit / 7700) * i for i in range(days + 1)]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, planned, "--", color="#5B8FD4", linewidth=2, label=f"计划减脂（每日缺口 {daily_deficit:.0f} kcal）")
    ax.axhline(start_weight - target_loss, color="red", linewidth=1, linestyle=":", label=f"目标体重 {start_weight - target_loss:.1f} kg")

    if trend_kgd is not None:
        trend_proj = [start_weight + trend_kgd * i for i in range(days + 1)]
        ax.plot(dates, trend_proj, "-", color="#E07B54", linewidth=1.5, label=f"当前趋势（{trend_kgd*7:+.2f} kg/周）")

    ax.set_title(f"减脂进度预测：{days} 天内减 {target_loss} kg")
    ax.set_ylabel("体重 (kg)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    fig.autofmt_xdate()
    ax.legend()
    ax.grid(alpha=0.3)
    out = REPORTS_DIR / f"plan_projection_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-loss", type=float, required=True, help="目标减脂量 (kg)")
    parser.add_argument("--days", type=int, required=True, help="计划天数")
    parser.add_argument("--weight", type=float, help="当前体重 kg（不填则从数据读取）")
    parser.add_argument("--height", type=float, default=170, help="身高 cm")
    parser.add_argument("--age", type=int, default=25)
    parser.add_argument("--gender", default="male")
    args = parser.parse_args()

    weight = args.weight or latest_weight()
    if not weight:
        print("无法获取体重，请通过 --weight 指定或先录入身体数据")
        sys.exit(1)

    weekly_w = weekly_workouts_from_data()
    activity = estimate_activity(weekly_w)
    bmr = mifflin_bmr(weight, args.height, args.age, args.gender)
    tdee = bmr * activity

    # 每天需要的热量缺口
    total_kcal = args.target_loss * 7700
    daily_deficit = total_kcal / args.days
    target_intake = tdee - daily_deficit

    trend = weight_trend()
    tag = date.today().strftime("%Y%m%d")

    print("\n=== 减脂计划分析 ===")
    print(f"当前体重：{weight} kg")
    print(f"目标：{args.days} 天内减 {args.target_loss} kg → 目标体重 {weight - args.target_loss:.1f} kg")
    print(f"估算 BMR：{bmr:.0f} kcal/天")
    print(f"活动系数：{activity}（每周约 {weekly_w:.1f} 次训练）")
    print(f"估算 TDEE：{tdee:.0f} kcal/天")
    print(f"所需热量缺口：{daily_deficit:.0f} kcal/天")
    print(f"建议每日摄入：{target_intake:.0f} kcal")
    if trend is not None:
        print(f"当前体重趋势：{trend*7:+.2f} kg/周")
        adj_days = args.target_loss / (-trend) if trend < 0 else None
        if adj_days:
            print(f"按当前趋势：约 {adj_days:.0f} 天达到目标（不调整饮食）")
    if daily_deficit > 1000:
        print("⚠️  每日缺口超过 1000 kcal，建议适当延长计划时间以避免肌肉流失")
    plot_projection(weight, args.target_loss, args.days, daily_deficit, trend, tag)
