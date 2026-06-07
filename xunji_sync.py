#!/usr/bin/env python3
"""
从训记 Open API 拉取训练数据，保存到 data/workouts/YYYY-MM.json
用法：python xunji_sync.py --date 2026-06-07
      python xunji_sync.py --month 2026-06
"""

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API_BASE = "https://trains.xunjiapp.cn"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('XUNJI_API_KEY', 'xjllm_04ee0e8043e87a919bb5c1efc7a697b9be2d329a53c205a7')}",
    "Content-Type": "application/json",
}
DATA_DIR = Path(__file__).parent / "data" / "workouts"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CACHE: dict[str, dict] = {}
LAST_REQUEST: dict[str, float] = {}
RATE_LIMIT_S = 90


def fetch_day(datestr: str, full: bool = False) -> dict:
    if datestr in CACHE:
        return CACHE[datestr]

    now = time.time()
    if datestr in LAST_REQUEST and now - LAST_REQUEST[datestr] < RATE_LIMIT_S:
        wait = RATE_LIMIT_S - (now - LAST_REQUEST[datestr])
        print(f"限频：{datestr} 需等待 {wait:.0f} 秒")
        time.sleep(wait)

    resp = requests.post(
        f"{API_BASE}/api_trains_for_llm_v2",
        headers=HEADERS,
        json={"schema_version": "train_open_api_v2", "datestr": datestr, "include_full_data": full},
        timeout=30,
    )
    LAST_REQUEST[datestr] = time.time()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"API 错误：{data}")
    CACHE[datestr] = data["res"]
    return data["res"]


def save_month(year: int, month: int, records: list[dict]):
    path = DATA_DIR / f"{year:04d}-{month:02d}.json"
    existing = []
    if path.exists():
        existing = json.loads(path.read_text())
    by_date = {r["datestr"]: r for r in existing}
    for r in records:
        by_date[r["datestr"]] = r
    merged = sorted(by_date.values(), key=lambda x: x["datestr"])
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"已保存 {len(merged)} 条训练到 {path}")


def sync_date(datestr: str):
    print(f"同步 {datestr} ...")
    res = fetch_day(datestr, full=True)
    trains = res.get("trains", [])
    if not trains:
        print(f"  {datestr} 无训练记录")
        return
    y, m, _ = datestr.split("-")
    save_month(int(y), int(m), trains)


def sync_month(year_month: str):
    y, m = map(int, year_month.split("-"))
    start = date(y, m, 1)
    end = date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)
    d = start
    all_trains = []
    while d < end:
        ds = d.strftime("%Y-%m-%d")
        try:
            res = fetch_day(ds, full=True)
            trains = res.get("trains", [])
            all_trains.extend(trains)
        except Exception as e:
            print(f"  {ds} 失败：{e}")
        d += timedelta(days=1)
    save_month(y, m, all_trains)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="同步单天，格式 YYYY-MM-DD")
    parser.add_argument("--month", help="同步整月，格式 YYYY-MM")
    args = parser.parse_args()
    if args.date:
        sync_date(args.date)
    elif args.month:
        sync_month(args.month)
    else:
        today = date.today().strftime("%Y-%m-%d")
        sync_date(today)
