#!/bin/bash
# 一键同步脚本 — 在 Mac 本地运行
# 用法：
#   ./sync.sh              同步今天的训记数据
#   ./sync.sh --month 2026-06   同步整月训记数据
#   ./sync.sh --health /path/to/导出.zip   解析健康App导出数据

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# ── 颜色输出 ──────────────────────────────────────────
green() { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
red() { echo -e "\033[31m$*\033[0m"; }

# ── 依赖检查 ──────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  red "需要 python3，请先安装：brew install python3"
  exit 1
fi

python3 -c "import requests" 2>/dev/null || {
  yellow "安装依赖..."
  pip3 install requests pandas -q
}

MODE="today"
HEALTH_ZIP=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --month) MODE="month"; MONTH="$2"; shift 2 ;;
    --health) MODE="health"; HEALTH_ZIP="$2"; shift 2 ;;
    --date) MODE="date"; DATE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ── 同步训记数据 ───────────────────────────────────────
sync_xunji() {
  local args=""
  case $MODE in
    today) args="--date $(date +%Y-%m-%d)" ;;
    date)  args="--date $DATE" ;;
    month) args="--month $MONTH" ;;
  esac
  green "同步训记数据 ($args)..."
  python3 "$REPO_DIR/xunji_sync.py" $args
}

# ── 解析健康App数据 ────────────────────────────────────
sync_health() {
  local zip="$HEALTH_ZIP"
  if [[ ! -f "$zip" ]]; then
    red "找不到文件：$zip"
    exit 1
  fi

  yellow "解压 $zip ..."
  local tmp=$(mktemp -d)
  unzip -q "$zip" -d "$tmp"

  local xml=$(find "$tmp" -name "导出.xml" | head -1)
  if [[ -z "$xml" ]]; then
    xml=$(find "$tmp" -name "export.xml" | head -1)
  fi
  if [[ -z "$xml" ]]; then
    red "zip 里找不到导出.xml"
    exit 1
  fi

  green "解析健康数据（文件较大，请稍候）..."
  python3 << PYEOF
import xml.etree.ElementTree as ET
import csv
from datetime import datetime
from pathlib import Path
from collections import defaultdict

xml_path = "$xml"
out_dir = Path("$REPO_DIR/data/body")
out_dir.mkdir(parents=True, exist_ok=True)

TYPES = {
    "HKQuantityTypeIdentifierBodyMass": "weight_kg",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat_pct",
    "HKQuantityTypeIdentifierLeanBodyMass": "muscle_kg",
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierHeartRate": "avg_hr",
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep_h",
}
SLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}

records = defaultdict(dict)

for event, elem in ET.iterparse(xml_path, events=["end"]):
    if elem.tag != "Record":
        elem.clear()
        continue
    rtype = elem.get("type", "")
    if rtype not in TYPES:
        elem.clear()
        continue
    field = TYPES[rtype]
    date = elem.get("startDate", "")[:10]
    val = elem.get("value", "")
    if field == "steps":
        records[date][field] = records[date].get(field, 0) + float(val or 0)
    elif field == "sleep_h":
        if val in SLEEP_VALUES:
            try:
                fmt = "%Y-%m-%d %H:%M:%S %z"
                s = datetime.strptime(elem.get("startDate"), fmt)
                e = datetime.strptime(elem.get("endDate"), fmt)
                records[date][field] = records[date].get(field, 0) + (e - s).total_seconds() / 3600
            except: pass
    elif field == "body_fat_pct":
        try:
            v = float(val)
            records[date][field] = f"{v*100:.1f}" if v < 1 else f"{v:.1f}"
        except: pass
    else:
        records[date][field] = val
    elem.clear()

# 按月分组，合并已有数据
from collections import defaultdict as dd
months = dd(dict)
for date, row in records.items():
    ym = date[:7]
    months[ym][date] = row

fields = ["date","weight_kg","body_fat_pct","muscle_kg","bmr","steps","resting_hr","avg_hr","sleep_h","notes"]
updated = []
for ym, day_rows in sorted(months.items()):
    path = out_dir / f"{ym}.csv"
    existing = {}
    if path.exists():
        with open(path) as f:
            for r in csv.DictReader(f):
                existing[r["date"]] = r
    for date, row in day_rows.items():
        rec = existing.get(date, {"date": date, "notes": ""})
        # 只更新非空字段
        for k, v in row.items():
            if v: rec[k] = str(v)
        if "steps" in rec and rec["steps"]:
            try: rec["steps"] = str(int(float(rec["steps"])))
            except: pass
        if "sleep_h" in rec and rec["sleep_h"]:
            try: rec["sleep_h"] = f"{float(rec['sleep_h']):.2f}"
            except: pass
        if "weight_kg" in rec and rec["weight_kg"]:
            try: rec["weight_kg"] = f"{float(rec['weight_kg']):.1f}"
            except: pass
        existing[date] = rec
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for date in sorted(existing):
            row = {k: existing[date].get(k, "") for k in fields}
            w.writerow(row)
    updated.append(ym)
    print(f"  已更新 {ym}（{len(existing)} 天）")

print(f"共更新 {len(updated)} 个月文件")
PYEOF

  rm -rf "$tmp"
}

# ── 执行 ───────────────────────────────────────────────
case $MODE in
  health) sync_health ;;
  *)      sync_xunji ;;
esac

# ── Git push ──────────────────────────────────────────
green "提交并推送..."
git add data/
git diff --cached --quiet && { yellow "没有新数据，跳过提交"; exit 0; }

COMMIT_MSG="sync: $(date '+%Y-%m-%d %H:%M')"
[[ $MODE == "health" ]] && COMMIT_MSG="sync health data: $(date '+%Y-%m-%d')"
[[ $MODE == "month" ]] && COMMIT_MSG="sync 训记 $MONTH"

git commit -m "$COMMIT_MSG"
git push origin HEAD

green "✓ 同步完成，数据已推送到 GitHub"
