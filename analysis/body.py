#!/usr/bin/env python3
"""
身体数据分析与可视化
用法：python analysis/body.py [--month 2026-06] [--all]
输出图表到 reports/
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

matplotlib.rcParams["font.family"] = ["SimHei", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

DATA_DIR = Path(__file__).parent.parent / "data" / "body"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def load_data(months: list[str] | None = None) -> pd.DataFrame:
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        print("没有找到身体数据文件，请先在 data/body/ 下放置 YYYY-MM.csv")
        sys.exit(1)
    dfs = []
    for f in files:
        if f.name == "template.csv":
            continue
        if months and f.stem not in months:
            continue
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            dfs.append(df)
        except Exception as e:
            print(f"读取 {f} 失败：{e}")
    if not dfs:
        print("没有匹配的数据")
        sys.exit(1)
    df = pd.concat(dfs).sort_values("date").drop_duplicates("date")
    return df


def plot_weight(df: pd.DataFrame, tag: str):
    if "weight_kg" not in df or df["weight_kg"].isna().all():
        return
    fig, ax = plt.subplots(figsize=(10, 4))
    d = df.dropna(subset=["weight_kg"])
    ax.plot(d["date"], d["weight_kg"], "o-", color="#E07B54", linewidth=2, markersize=4)
    # 7日均线
    if len(d) >= 7:
        ax.plot(d["date"], d["weight_kg"].rolling(7, center=True).mean(),
                "--", color="#888", linewidth=1.5, label="7日均线")
        ax.legend()
    ax.set_title("体重趋势 (kg)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    fig.autofmt_xdate()
    ax.grid(axis="y", alpha=0.3)
    out = REPORTS_DIR / f"body_weight_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def plot_steps(df: pd.DataFrame, tag: str):
    if "steps" not in df or df["steps"].isna().all():
        return
    fig, ax = plt.subplots(figsize=(10, 3))
    d = df.dropna(subset=["steps"])
    ax.bar(d["date"], d["steps"], color="#5B8FD4", width=0.8)
    ax.axhline(8000, color="red", linestyle="--", linewidth=1, label="8000步目标")
    ax.legend()
    ax.set_title("每日步数")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    fig.autofmt_xdate()
    ax.grid(axis="y", alpha=0.3)
    out = REPORTS_DIR / f"body_steps_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def plot_hr(df: pd.DataFrame, tag: str):
    cols = [c for c in ["resting_hr", "avg_hr"] if c in df.columns]
    if not cols:
        return
    fig, ax = plt.subplots(figsize=(10, 3))
    colors = {"resting_hr": "#E07B54", "avg_hr": "#5B8FD4"}
    labels = {"resting_hr": "静息心率", "avg_hr": "平均心率"}
    for c in cols:
        d = df.dropna(subset=[c])
        if d.empty:
            continue
        ax.plot(d["date"], d[c], "o-", color=colors[c], label=labels[c], linewidth=1.5, markersize=3)
    ax.set_title("心率 (bpm)")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    fig.autofmt_xdate()
    ax.grid(axis="y", alpha=0.3)
    out = REPORTS_DIR / f"body_hr_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def summary(df: pd.DataFrame):
    print("\n=== 身体数据摘要 ===")
    print(f"数据范围：{df['date'].min().date()} → {df['date'].max().date()}（{len(df)} 天）")
    if "weight_kg" in df:
        w = df["weight_kg"].dropna()
        if not w.empty:
            print(f"体重：最新 {w.iloc[-1]:.1f} kg，最高 {w.max():.1f}，最低 {w.min():.1f}，变化 {w.iloc[-1]-w.iloc[0]:+.1f} kg")
    if "steps" in df:
        s = df["steps"].dropna()
        if not s.empty:
            print(f"步数：日均 {s.mean():.0f} 步，达标天数（≥8000）{(s>=8000).sum()} 天")
    if "resting_hr" in df:
        h = df["resting_hr"].dropna()
        if not h.empty:
            print(f"静息心率：均值 {h.mean():.0f} bpm")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="指定月份 YYYY-MM（可多个，逗号分隔）")
    parser.add_argument("--all", action="store_true", help="分析所有数据")
    args = parser.parse_args()

    months = args.month.split(",") if args.month else None
    df = load_data(months)
    tag = date.today().strftime("%Y%m%d")

    summary(df)
    plot_weight(df, tag)
    plot_steps(df, tag)
    plot_hr(df, tag)
