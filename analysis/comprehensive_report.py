#!/usr/bin/env python3
"""Comprehensive fitness analysis report generator."""

import os
import glob
import json
import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import numpy as np
import pandas as pd

import matplotlib
import matplotlib.font_manager as fm
matplotlib.use("Agg")
for path in [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]:
    try:
        fm.fontManager.addfont(path)
    except Exception:
        pass
matplotlib.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

REPORTS_DIR = "/home/user/fitness-tracker/reports"
BODY_DIR = "/home/user/fitness-tracker/data/body"
WORKOUT_DIR = "/home/user/fitness-tracker/data/workouts"
os.makedirs(REPORTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# LOAD BODY DATA
# ─────────────────────────────────────────────
def load_body_data():
    frames = []
    for f in sorted(glob.glob(os.path.join(BODY_DIR, "*.csv"))):
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            frames.append(df)
        except Exception as e:
            print(f"  [warn] body {f}: {e}")
    body = pd.concat(frames, ignore_index=True)
    body = body.sort_values("date").reset_index(drop=True)
    # fix body_fat_pct: values < 1 are fractions → multiply by 100
    mask = body["body_fat_pct"].notna() & (body["body_fat_pct"] < 1)
    body.loc[mask, "body_fat_pct"] = body.loc[mask, "body_fat_pct"] * 100
    return body


# ─────────────────────────────────────────────
# LOAD WORKOUT DATA
# ─────────────────────────────────────────────
LBS_TO_KG = 0.4536

def load_workout_data():
    sessions = []
    for f in sorted(glob.glob(os.path.join(WORKOUT_DIR, "*.json"))):
        try:
            with open(f) as fh:
                data = json.load(fh)
            for w in data:
                sessions.append(w)
        except Exception as e:
            print(f"  [warn] workout {f}: {e}")
    return sessions


def get_weight_kg(set_obj):
    """Return weight in kg from a set object. Returns None if not applicable."""
    w = set_obj.get("weight", "")
    if not w or str(w).strip() == "":
        return None
    try:
        w = float(w)
    except (ValueError, TypeError):
        return None
    unit = set_obj.get("unit", "lbs").strip().lower()
    if unit == "kg":
        return w
    else:  # lbs or empty → assume lbs
        return w * LBS_TO_KG


def session_volume(workout):
    """Total volume (kg × reps) for done sets in a session."""
    total = 0.0
    for m in workout.get("movements", []):
        for s in m.get("sets", []):
            if not s.get("done", False):
                continue
            wkg = get_weight_kg(s)
            if wkg is None:
                continue
            reps = s.get("reps", "")
            try:
                reps = int(reps)
            except (ValueError, TypeError):
                continue
            total += wkg * reps
    return total


MUSCLE_MAP = {
    "胸": "胸",
    "卧推": "胸",
    "飞鸟": "胸",
    "夹胸": "胸",
    "背": "背",
    "划船": "背",
    "下拉": "背",
    "引体": "背",
    "硬拉": "背/腿",
    "腿": "腿",
    "深蹲": "腿",
    "腿举": "腿",
    "弓步": "腿",
    "腿屈伸": "腿",
    "腿弯举": "腿",
    "臀": "臀",
    "肩": "肩",
    "推举": "肩",
    "侧平举": "肩",
    "前平举": "肩",
    "二头": "二头",
    "弯举": "二头",
    "三头": "三头",
    "臂屈伸": "三头",
    "绳索下压": "三头",
    "核心": "核心",
    "腹": "核心",
    "平板支撑": "核心",
    "卷腹": "核心",
}

def infer_muscle(name):
    for kw, group in MUSCLE_MAP.items():
        if kw in name:
            return group
    return "其他"


# ─────────────────────────────────────────────
# 1. 体重长期趋势图
# ─────────────────────────────────────────────
def chart_weight_trend(body):
    df = body[["date", "weight_kg"]].dropna().copy()
    df = df.sort_values("date")
    roll = df.set_index("date")["weight_kg"].rolling(30, min_periods=3).mean()

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df["date"], df["weight_kg"], color="#B0C4DE", linewidth=0.8, alpha=0.7, label="每日体重")
    ax.plot(roll.index, roll.values, color="#2166AC", linewidth=2.2, label="30天滚动均值")

    # Trend line
    x_num = np.arange(len(df))
    z = np.polyfit(x_num, df["weight_kg"].values.astype(float), 1)
    p = np.poly1d(z)
    ax.plot(df["date"], p(x_num), "--", color="#D94F2B", linewidth=1.5, alpha=0.7, label="线性趋势")

    # Milestones
    idx_min = df["weight_kg"].idxmin()
    idx_max = df["weight_kg"].idxmax()
    idx_cur = df.index[-1]
    for idx, label, color in [(idx_min, f"最低\n{df.loc[idx_min,'weight_kg']:.1f}kg", "#27AE60"),
                               (idx_max, f"最高\n{df.loc[idx_max,'weight_kg']:.1f}kg", "#E74C3C"),
                               (idx_cur, f"当前\n{df.loc[idx_cur,'weight_kg']:.1f}kg", "#8E44AD")]:
        ax.annotate(label,
                    xy=(df.loc[idx, "date"], df.loc[idx, "weight_kg"]),
                    xytext=(0, 18), textcoords="offset points",
                    ha="center", fontsize=9, color=color,
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2))
        ax.scatter([df.loc[idx, "date"]], [df.loc[idx, "weight_kg"]], color=color, s=60, zorder=5)

    ax.set_title("体重长期趋势（2020–2026）", fontsize=14, pad=12)
    ax.set_xlabel("日期")
    ax.set_ylabel("体重 (kg)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "body_weight_trend.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 2. 体重近6个月
# ─────────────────────────────────────────────
def chart_weight_recent(body):
    start = pd.Timestamp("2025-12-01")
    df = body[["date", "weight_kg"]].dropna().copy()
    df = df[df["date"] >= start].sort_values("date")
    roll7 = df.set_index("date")["weight_kg"].rolling(7, min_periods=2).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(df["date"], df["weight_kg"], color="#5B9BD5", s=22, zorder=4, alpha=0.8, label="每日体重")
    ax.plot(df["date"], df["weight_kg"], color="#A9C8E8", linewidth=0.8, alpha=0.5)
    ax.plot(roll7.index, roll7.values, color="#E8540B", linewidth=2.2, label="7天滚动均值")

    ax.set_title("近6个月体重变化（2025-12 至 2026-06）", fontsize=13)
    ax.set_xlabel("日期")
    ax.set_ylabel("体重 (kg)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "body_weight_recent.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 3. 体脂率趋势
# ─────────────────────────────────────────────
def chart_body_fat(body):
    df = body[["date", "body_fat_pct"]].dropna().copy()
    df = df.sort_values("date")
    if df.empty:
        print("  [skip] no body_fat_pct data")
        return
    roll = df.set_index("date")["body_fat_pct"].rolling(60, min_periods=3).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(df["date"], df["body_fat_pct"], color="#FF8C69", s=20, alpha=0.7, zorder=4, label="体脂率")
    ax.plot(roll.index, roll.values, color="#CC3300", linewidth=2.2, label="60天滚动均值")

    # reference lines
    ax.axhline(25, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax.text(df["date"].min(), 25.3, "健康上限 25%", fontsize=8, color="gray")

    ax.set_title("体脂率趋势", fontsize=13)
    ax.set_xlabel("日期")
    ax.set_ylabel("体脂率 (%)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "body_fat_trend.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 4. 步数分析
# ─────────────────────────────────────────────
def chart_steps(body):
    df = body[["date", "steps"]].dropna().copy()
    df["date"] = pd.to_datetime(df["date"])
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce")
    df = df.dropna().copy()
    df = df[df["steps"] > 0].sort_values("date")
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month")["steps"].mean().reset_index()
    monthly["month_str"] = monthly["month"].astype(str)

    GOAL = 8000
    colors = ["#2ECC71" if v >= GOAL else "#E74C3C" for v in monthly["steps"]]

    fig, ax = plt.subplots(figsize=(16, 5))
    bars = ax.bar(range(len(monthly)), monthly["steps"], color=colors, edgecolor="white", linewidth=0.4)
    ax.axhline(GOAL, color="#3498DB", linestyle="--", linewidth=1.5, label=f"目标 {GOAL} 步/天")
    ax.set_xticks(range(len(monthly)))
    ax.set_xticklabels(monthly["month_str"], rotation=60, ha="right", fontsize=7)
    ax.set_title("每月平均步数（绿色=达标，红色=未达标）", fontsize=13)
    ax.set_ylabel("平均步数")
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "body_steps.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 5. 训练频率热力图
# ─────────────────────────────────────────────
def chart_workout_heatmap(sessions):
    dates = set()
    for w in sessions:
        d = w.get("datestr", "")
        if d:
            try:
                dates.add(pd.Timestamp(d).date())
            except Exception:
                pass

    start = pd.Timestamp("2025-01-01").date()
    end = pd.Timestamp("2026-06-10").date()

    # Build weekly grid: rows=weekday (Mon-Sun), cols=weeks
    all_days = pd.date_range(start, end, freq="D")
    # Week index from start (Monday-aligned)
    week_start = pd.Timestamp(start) - pd.Timedelta(days=pd.Timestamp(start).weekday())
    weeks = sorted(set(((d - week_start).days // 7) for d in all_days))
    n_weeks = len(weeks)

    grid = np.zeros((7, n_weeks))
    week_labels = {}
    for d in all_days:
        dow = d.weekday()  # 0=Mon
        wk = (d - week_start).days // 7
        wi = weeks.index(wk)
        grid[dow, wi] = 1 if d.date() in dates else 0
        if dow == 0:
            week_labels[wi] = d.strftime("%Y-%m")

    # Month labels at first Monday of each month
    month_positions = {}
    for wi, label in week_labels.items():
        if label not in month_positions:
            month_positions[label] = wi

    cmap = LinearSegmentedColormap.from_list("gym", ["#EEEEEE", "#1A7ABF"])
    fig, ax = plt.subplots(figsize=(20, 3.5))
    ax.imshow(grid, cmap=cmap, aspect="auto", vmin=0, vmax=1, interpolation="nearest")

    # Month tick labels
    sorted_months = sorted(month_positions.items(), key=lambda x: x[1])
    ax.set_xticks([v for _, v in sorted_months])
    ax.set_xticklabels([k for k, _ in sorted_months], rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(7))
    ax.set_yticklabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"], fontsize=8)
    ax.set_title(f"训练日历热力图（2025-01 至 2026-06）  共训练 {len(dates)} 天", fontsize=13)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "workout_heatmap.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 6. 训练容量趋势
# ─────────────────────────────────────────────
def chart_workout_volume(sessions):
    records = []
    for w in sessions:
        d = w.get("datestr", "")
        if not d:
            continue
        vol = session_volume(w)
        records.append({"date": pd.Timestamp(d), "volume": vol})
    if not records:
        return
    df = pd.DataFrame(records).sort_values("date")
    df = df[df["volume"] > 0]
    roll4 = df["volume"].rolling(4, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(df["date"], df["volume"], color="#A8CBE8", alpha=0.6, width=1.2, label="单次训练容量")
    ax.plot(df["date"], roll4, color="#1F5FA6", linewidth=2, label="4次滚动均值")
    ax.set_title("训练容量趋势（kg × reps）", fontsize=13)
    ax.set_xlabel("日期")
    ax.set_ylabel("训练容量 (kg·次)")
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "workout_volume.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


# ─────────────────────────────────────────────
# 7. 动作进步曲线 (e1RM)
# ─────────────────────────────────────────────
def chart_workout_progress(sessions):
    # collect best e1RM per exercise per date
    ex_data = {}
    for w in sessions:
        d = w.get("datestr", "")
        if not d:
            continue
        date = pd.Timestamp(d)
        for m in w.get("movements", []):
            name = m.get("name", "")
            if not name:
                continue
            best_e1rm = 0
            for s in m.get("sets", []):
                if not s.get("done", False):
                    continue
                wkg = get_weight_kg(s)
                if wkg is None or wkg <= 0:
                    continue
                reps_raw = s.get("reps", "")
                try:
                    reps = int(reps_raw)
                except (ValueError, TypeError):
                    continue
                if reps <= 0:
                    continue
                e1rm = wkg * (1 + reps / 30)
                if e1rm > best_e1rm:
                    best_e1rm = e1rm
            if best_e1rm > 0:
                if name not in ex_data:
                    ex_data[name] = []
                ex_data[name].append((date, best_e1rm))

    # Pick top exercises by session count
    ex_counts = {k: len(v) for k, v in ex_data.items()}
    top_ex = sorted(ex_counts, key=lambda x: -ex_counts[x])[:8]

    colors_list = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728",
                   "#9467BD", "#8C564B", "#E377C2", "#7F7F7F"]

    fig, ax = plt.subplots(figsize=(14, 6))
    for i, name in enumerate(top_ex):
        pts = sorted(ex_data[name], key=lambda x: x[0])
        dates = [p[0] for p in pts]
        vals = [p[1] for p in pts]
        # Smooth with rolling
        s_series = pd.Series(vals).rolling(5, min_periods=1).max()
        ax.plot(s_series.index, s_series.values, color=colors_list[i % len(colors_list)],
                linewidth=1.8, label=name)

    ax.set_title("主要动作估算1RM进步曲线（e1RM = 重量×(1+次数/30)）", fontsize=12)
    ax.set_xlabel("日期")
    ax.set_ylabel("估算1RM (kg)")
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "workout_progress.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")
    return ex_data


# ─────────────────────────────────────────────
# 8. 肌群训练分布
# ─────────────────────────────────────────────
def chart_muscle_dist(sessions):
    muscle_vol = {}
    for w in sessions:
        for m in w.get("movements", []):
            name = m.get("name", "")
            group = infer_muscle(name)
            vol = 0
            for s in m.get("sets", []):
                if not s.get("done", False):
                    continue
                wkg = get_weight_kg(s)
                if wkg is None:
                    continue
                reps_raw = s.get("reps", "")
                try:
                    reps = int(reps_raw)
                except (ValueError, TypeError):
                    continue
                vol += wkg * reps
            if vol > 0:
                muscle_vol[group] = muscle_vol.get(group, 0) + vol

    if not muscle_vol:
        return
    groups = sorted(muscle_vol, key=lambda x: -muscle_vol[x])
    vols = [muscle_vol[g] for g in groups]
    total = sum(vols)
    pcts = [v / total * 100 for v in vols]

    palette = ["#2166AC", "#4DAC26", "#D01C8B", "#F1A340",
               "#998EC3", "#F7F7F7", "#D9EF8B", "#A6D96A", "#E08214"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie
    wedge_colors = palette[:len(groups)]
    wedges, texts, autotexts = ax1.pie(
        vols, labels=groups, autopct="%1.1f%%",
        colors=wedge_colors, startangle=140,
        pctdistance=0.75, textprops={"fontsize": 9})
    ax1.set_title("各肌群训练容量占比", fontsize=12)

    # Bar
    ax2.barh(groups[::-1], [muscle_vol[g] / 1000 for g in groups[::-1]],
             color=wedge_colors[::-1], edgecolor="white")
    ax2.set_xlabel("总训练容量 (ton·次)")
    ax2.set_title("各肌群总训练容量", fontsize=12)
    ax2.grid(True, axis="x", alpha=0.3)

    fig.tight_layout()
    out = os.path.join(REPORTS_DIR, "workout_muscle_dist.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")
    return muscle_vol


# ─────────────────────────────────────────────
# TEXT SUMMARY
# ─────────────────────────────────────────────
def print_summary(body, sessions, ex_data, muscle_vol):
    print("\n" + "="*65)
    print("        综合健身分析文字摘要")
    print("="*65)

    # Weight stats
    bw = body[["date", "weight_kg"]].dropna().sort_values("date")
    w_start = bw.iloc[0]
    w_cur = bw.iloc[-1]
    w_min = bw.loc[bw["weight_kg"].idxmin()]
    w_max = bw.loc[bw["weight_kg"].idxmax()]
    print(f"\n【体重历史】")
    print(f"  起始记录：{w_start['date'].date()}  {w_start['weight_kg']:.1f} kg")
    print(f"  最高体重：{w_max['date'].date()}  {w_max['weight_kg']:.1f} kg")
    print(f"  最低体重：{w_min['date'].date()}  {w_min['weight_kg']:.1f} kg")
    print(f"  当前体重：{w_cur['date'].date()}  {w_cur['weight_kg']:.1f} kg")
    print(f"  净变化：{w_cur['weight_kg'] - w_start['weight_kg']:+.1f} kg（6年总计）")

    # Recent 3 months
    three_m_ago = pd.Timestamp("2026-03-01")
    recent = bw[bw["date"] >= three_m_ago]
    if len(recent) >= 2:
        delta3m = recent.iloc[-1]["weight_kg"] - recent.iloc[0]["weight_kg"]
        print(f"\n【近3个月体重趋势（2026-03 至今）】")
        print(f"  从 {recent.iloc[0]['weight_kg']:.1f} kg → {recent.iloc[-1]['weight_kg']:.1f} kg，变化 {delta3m:+.1f} kg")

    # Body fat
    bf = body[["date", "body_fat_pct"]].dropna().sort_values("date")
    if not bf.empty:
        print(f"\n【体脂率】")
        print(f"  最早记录：{bf.iloc[0]['date'].date()}  {bf.iloc[0]['body_fat_pct']:.1f}%")
        print(f"  最新记录：{bf.iloc[-1]['date'].date()}  {bf.iloc[-1]['body_fat_pct']:.1f}%")
        print(f"  最低记录：{bf['body_fat_pct'].min():.1f}%")

    # Training consistency
    print(f"\n【训练一致性 — 每月训练场次】")
    month_counts = {}
    for w in sessions:
        d = w.get("datestr", "")
        if d:
            try:
                m = pd.Timestamp(d).to_period("M").strftime("%Y-%m")
                month_counts[m] = month_counts.get(m, 0) + 1
            except Exception:
                pass
    for month in sorted(month_counts):
        bar = "█" * month_counts[month]
        print(f"  {month}  {month_counts[month]:3d} 次  {bar}")
    total_sessions = sum(month_counts.values())
    months_span = len(month_counts)
    print(f"  → 共 {total_sessions} 次，平均 {total_sessions/months_span:.1f} 次/月")

    # Top 5 exercises by set count
    print(f"\n【训练频率 Top 5 动作（按总组数）】")
    ex_sets = {}
    for w in sessions:
        for m in w.get("movements", []):
            name = m.get("name", "")
            done_sets = sum(1 for s in m.get("sets", []) if s.get("done", False))
            if done_sets > 0:
                ex_sets[name] = ex_sets.get(name, 0) + done_sets
    top5 = sorted(ex_sets, key=lambda x: -ex_sets[x])[:5]
    for rank, name in enumerate(top5, 1):
        print(f"  {rank}. {name}：{ex_sets[name]} 组")

    # Strength progression
    print(f"\n【力量进步亮点（e1RM 最大提升）】")
    improvements = []
    for name, pts in ex_data.items():
        if len(pts) < 3:
            continue
        pts_sorted = sorted(pts, key=lambda x: x[0])
        e1rms = [p[1] for p in pts_sorted]
        first3_avg = np.mean(e1rms[:3])
        last3_avg = np.mean(e1rms[-3:])
        if first3_avg > 0:
            pct = (last3_avg - first3_avg) / first3_avg * 100
            improvements.append((name, first3_avg, last3_avg, pct))
    improvements.sort(key=lambda x: -x[3])
    for name, f, l, pct in improvements[:5]:
        print(f"  {name}：{f:.1f} kg → {l:.1f} kg  ({pct:+.1f}%)")

    # Muscle distribution
    if muscle_vol:
        total_vol = sum(muscle_vol.values())
        print(f"\n【肌群训练分布 Top 5（按容量占比）】")
        for g in sorted(muscle_vol, key=lambda x: -muscle_vol[x])[:5]:
            pct = muscle_vol[g] / total_vol * 100
            print(f"  {g}：{pct:.1f}%")

    # Notable insights
    print(f"\n【主要观察与建议】")
    # Weight trend
    if len(bw) >= 60:
        last_60 = bw.tail(60)
        x = np.arange(len(last_60))
        z = np.polyfit(x, last_60["weight_kg"].values.astype(float), 1)
        slope_per_week = z[0] * 7
        if slope_per_week < -0.2:
            print(f"  ✓ 近期体重下降趋势明显（约 {abs(slope_per_week):.2f} kg/周），减脂进展良好")
        elif slope_per_week < 0:
            print(f"  → 近期体重缓慢下降（约 {abs(slope_per_week):.2f} kg/周），可适当加大热量缺口")
        else:
            print(f"  ! 近期体重稳定或略升（约 {slope_per_week:+.2f} kg/周），建议检查饮食与训练强度")

    # Steps
    steps_df = body[["date", "steps"]].dropna()
    steps_df = steps_df[steps_df["steps"] > 0]
    if not steps_df.empty:
        recent_steps = steps_df[steps_df["date"] >= pd.Timestamp("2026-03-01")]
        if not recent_steps.empty:
            avg = recent_steps["steps"].mean()
            print(f"  → 近3个月平均步数：{avg:.0f} 步/天（目标 8000）",
                  "✓达标" if avg >= 8000 else "× 未达标，建议增加日常活动")

    print("\n" + "="*65)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("加载数据...")
    body = load_body_data()
    sessions = load_workout_data()
    print(f"  体重记录：{len(body)} 行，训练场次：{len(sessions)}")

    print("\n生成图表...")
    chart_weight_trend(body)
    chart_weight_recent(body)
    chart_body_fat(body)
    chart_steps(body)
    chart_workout_heatmap(sessions)
    chart_workout_volume(sessions)
    ex_data = chart_workout_progress(sessions)
    muscle_vol = chart_muscle_dist(sessions)

    print_summary(body, sessions, ex_data or {}, muscle_vol or {})


if __name__ == "__main__":
    main()
