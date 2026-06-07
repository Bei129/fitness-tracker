# fitness-tracker
💪 个人力量训练记录 & 身体数据分析 & 减脂计划管理

## 目录结构
```
fitness-tracker/
├── data/
│   ├── body/          # 身体数据（体重、心率、步数等）CSV，按月存储
│   └── workouts/      # 训记训练数据 JSON，按月存储
├── analysis/
│   ├── body.py        # 身体数据分析 + 可视化
│   ├── workouts.py    # 训练量、动作频率、进步曲线
│   └── plan.py        # 减脂目标分析（TDEE、热量缺口、进度预测）
├── reports/           # 生成的图表（PNG）
├── xunji_sync.py      # 从训记 API 同步训练数据
└── requirements.txt
```

## 快速开始

```bash
pip install -r requirements.txt

# 同步今天的训练
python xunji_sync.py

# 同步某月全部训练
python xunji_sync.py --month 2026-06

# 分析身体数据
python analysis/body.py --month 2026-06

# 分析训练数据
python analysis/workouts.py --all
python analysis/workouts.py --movement 杠铃卧推   # 某动作进步曲线

# 减脂计划分析（60天减5kg，身高175，年龄28）
python analysis/plan.py --target-loss 5 --days 60 --height 175 --age 28
```

## 身体数据录入格式
在 `data/body/YYYY-MM.csv` 中按以下格式录入，没有的字段留空：
```
date,weight_kg,body_fat_pct,muscle_kg,bmr,steps,resting_hr,avg_hr,sleep_h,notes
2026-06-01,75.2,22.1,,,,62,,,
```

## 与 Claude 协作
直接告诉 Claude：
- "同步训记 6 月数据" → 调用 API 拉取并保存
- "分析本月训练" → 运行 workouts.py 生成图表
- "我想 90 天减 8kg，身高 172，体重 80" → 运行 plan.py 给出分析
- 粘贴 iOS 健康 App 数据 → 自动整理写入 CSV
