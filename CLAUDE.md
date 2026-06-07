# Fitness Tracker — Claude 工作说明

## 仓库用途
记录并分析力量训练、身体数据，辅助制定减脂计划。

## 数据来源
| 类型 | 来源 | 存储位置 |
|------|------|----------|
| 力量训练 | 训记 App Open API | `data/workouts/YYYY-MM.json` |
| 身体数据 | 用户手动提供（来自 iOS 健康 App） | `data/body/YYYY-MM.csv` |
| 生成图表 | analysis/ 脚本输出 | `reports/` |

## 训记 API
- 读取/写回规则见会话中的"训记训练数据 Open API Skill"
- 同步脚本：`xunji_sync.py`
- 动作名只使用中文，不暴露内部 key

## 身体数据格式（data/body/YYYY-MM.csv）
```
date,weight_kg,body_fat_pct,muscle_kg,bmr,steps,resting_hr,avg_hr,sleep_h,notes
2026-06-01,75.2,22.1,,,,62,,,
```
- 没有的字段留空即可，date 为 YYYY-MM-DD

## 工作流程
1. **同步训练**：用户说"同步训记数据"→ 调用 xunji_sync.py 或直接调 API
2. **录入身体数据**：用户粘贴数据 → 追加到对应月份 CSV
3. **分析**：调用 analysis/ 下的脚本，输出图表到 reports/
4. **减脂计划分析**：用户给出目标（天数+kg）→ plan.py 结合现有数据给出热量缺口、训练建议

## 分析脚本说明
- `analysis/body.py`：体重趋势、体脂、步数、心率可视化
- `analysis/workouts.py`：训练量、动作进步、肌群分布可视化
- `analysis/plan.py`：减脂目标分析（TDEE 估算、热量缺口、进度预测）
- 所有图表保存到 `reports/`，文件名带日期

## 注意
- 不要删除 data/ 下的历史数据
- 写回训记前必须展示变更摘要等用户确认
- 图表使用中文标签，matplotlib 用 SimHei 或 sans-serif 回退
