#!/usr/bin/env python3
"""
训练数据分析与可视化
用法：python analysis/workouts.py [--month 2026-06] [--all]
输出图表到 reports/
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

matplotlib.rcParams["font.family"] = ["SimHei", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

DATA_DIR = Path(__file__).parent.parent / "data" / "workouts"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def load_data(months: list[str] | None = None) -> list[dict]:
    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print("没有找到训练数据，请先运行 xunji_sync.py 同步数据")
        sys.exit(1)
    trains = []
    for f in files:
        if months and f.stem not in months:
            continue
        try:
            data = json.loads(f.read_text())
            trains.extend(data)
        except Exception as e:
            print(f"读取 {f} 失败：{e}")
    trains.sort(key=lambda x: x.get("datestr", ""))
    return trains


def compute_volume(trains: list[dict]) -> pd.DataFrame:
    """每次训练的总容量（kg × reps）"""
    rows = []
    for t in trains:
        ds = t.get("datestr", "")
        title = t.get("title", "")
        vol = 0
        sets_count = 0
        movements = t.get("movements", [])
        for mv in movements:
            for s in mv.get("sets", []):
                if not s.get("done", True):
                    continue
                try:
                    w = float(s.get("weight", 0) or 0)
                    r = float(s.get("reps", 0) or 0)
                    vol += w * r
                    sets_count += 1
                except Exception:
                    pass
        rows.append({"date": pd.to_datetime(ds), "title": title, "volume_kg": vol, "sets": sets_count,
                     "movements": len(movements)})
    return pd.DataFrame(rows)


def movement_freq(trains: list[dict]) -> pd.Series:
    freq: dict[str, int] = defaultdict(int)
    for t in trains:
        for mv in t.get("movements", []):
            name = mv.get("name", "未知")
            done_sets = sum(1 for s in mv.get("sets", []) if s.get("done", True))
            freq[name] += done_sets
    return pd.Series(freq).sort_values(ascending=False)


def plot_volume(df: pd.DataFrame, tag: str):
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(df["date"], df["volume_kg"], color="#5B8FD4", width=0.8)
    ax.set_title("每次训练总容量 (kg × reps)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    fig.autofmt_xdate()
    ax.grid(axis="y", alpha=0.3)
    out = REPORTS_DIR / f"workout_volume_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def plot_freq(freq: pd.Series, tag: str, top_n: int = 15):
    if freq.empty:
        return
    data = freq.head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(4, len(data) * 0.4)))
    ax.barh(data.index[::-1], data.values[::-1], color="#E07B54")
    ax.set_title(f"最常做的 {top_n} 个动作（已完成组数）")
    ax.set_xlabel("已完成组数")
    fig.tight_layout()
    out = REPORTS_DIR / f"workout_freq_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def plot_movement_progress(trains: list[dict], name: str, tag: str):
    """单个动作的最大重量进步曲线"""
    rows = []
    for t in trains:
        ds = t.get("datestr", "")
        for mv in t.get("movements", []):
            if mv.get("name") != name:
                continue
            weights = []
            for s in mv.get("sets", []):
                if not s.get("done", True):
                    continue
                try:
                    weights.append(float(s.get("weight", 0) or 0))
                except Exception:
                    pass
            if weights:
                rows.append({"date": pd.to_datetime(ds), "max_weight": max(weights)})
    if not rows:
        return
    df = pd.DataFrame(rows).sort_values("date")
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(df["date"], df["max_weight"], "o-", color="#5B8FD4", linewidth=2)
    ax.set_title(f"{name} — 最大重量进步 (kg)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    fig.autofmt_xdate()
    ax.grid(axis="y", alpha=0.3)
    safe_name = name.replace("/", "_")
    out = REPORTS_DIR / f"progress_{safe_name}_{tag}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成：{out}")


def summary(trains: list[dict], vol_df: pd.DataFrame):
    print("\n=== 训练数据摘要 ===")
    print(f"总训练次数：{len(trains)}")
    if not vol_df.empty:
        print(f"日期范围：{vol_df['date'].min().date()} → {vol_df['date'].max().date()}")
        print(f"总训练容量：{vol_df['volume_kg'].sum():.0f} kg·reps")
        print(f"平均每次容量：{vol_df['volume_kg'].mean():.0f} kg·reps")
        print(f"平均每次动作数：{vol_df['movements'].mean():.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="指定月份 YYYY-MM（可多个，逗号分隔）")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--movement", help="生成指定动作的进步曲线")
    args = parser.parse_args()

    months = args.month.split(",") if args.month else None
    trains = load_data(months)
    tag = date.today().strftime("%Y%m%d")

    vol_df = compute_volume(trains)
    freq = movement_freq(trains)

    summary(trains, vol_df)
    plot_volume(vol_df, tag)
    plot_freq(freq, tag)
    if args.movement:
        plot_movement_progress(trains, args.movement, tag)
