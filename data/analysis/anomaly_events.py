# -*- coding: utf-8 -*-
"""
子系统四（下）：异常事件聚合与结构化归因，填充 anomaly_events
  1. 读 anomaly_hourly，每个城市把连续 is_anomaly=1 的小时段合并（>=6 小时才算事件）
  2. 窗口统计：起止时间、持续时长、PM2.5/AQI 峰值与峰值时刻
  3. 归因：窗口内各污染物相对该城市历史同时刻（city,hour）均值的 Z-score 排序，
     偏离最大者 = 主控污染物；完整排序写入 attribution JSON
连接参数走环境变量（见 pipeline_common.py）；先跑 anomaly_iforest.py。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from sqlalchemy import text

from pipeline_common import MEASURE, get_engine

engine = get_engine()
MIN_HOURS = 6

print("读取异常分数明细...")
a = pd.read_sql("SELECT city, date, hour, is_anomaly FROM anomaly_hourly", engine)
a["date"] = pd.to_datetime(a["date"])
a["ts"] = a["date"] + pd.to_timedelta(a["hour"], unit="h")

print("读取明细污染物值...")
d = pd.read_sql("SELECT city, date, hour, {} FROM air_quality_detail".format(
    ",".join(MEASURE)), engine)
d["date"] = pd.to_datetime(d["date"])
d["ts"] = d["date"] + pd.to_timedelta(d["hour"], unit="h")
m = a.merge(d, on=["city", "date", "hour", "ts"], how="left")

# 归因基线：每 (city, hour) 的污染物均值/标准差
base_mean = d.groupby(["city", "hour"])[MEASURE].mean()
base_std = d.groupby(["city", "hour"])[MEASURE].std().replace(0, np.nan)

events = []
for city, g in m[m.is_anomaly == 1].sort_values("ts").groupby("city"):
    g = g.reset_index(drop=True)
    gap = g["ts"].diff() != pd.Timedelta(hours=1)     # 相邻异常小时出现断档 -> 新窗口
    g["win"] = gap.cumsum()
    for _, w in g.groupby("win"):
        if len(w) < MIN_HOURS:
            continue
        # 窗口内各污染物相对 (city,hour) 基线的 Z-score
        zs = {}
        for col in MEASURE:
            mu = base_mean.loc[(city, w["hour"].iloc[0]), col]
            sd = base_std.loc[(city, w["hour"].iloc[0]), col]
            zs[col] = round(float((w[col].mean() - mu) / sd), 2) if sd and sd == sd else 0.0
        zs = {k: (0.0 if v != v else v) for k, v in zs.items()}   # NaN -> 0（JSON 不允许 NaN）
        zs_sorted = dict(sorted(zs.items(), key=lambda kv: -abs(kv[1])))
        main = max(zs_sorted, key=lambda k: zs_sorted[k])
        pk = w.loc[w["pm25"].idxmax()]
        events.append({
            "city": city,
            "start_time": w["ts"].iloc[0],
            "end_time": w["ts"].iloc[-1],
            "duration_hours": int(len(w)),
            "peak_pm25": float(pk["pm25"]),
            "peak_aqi": float(w["aqi"].max()),
            "peak_time": w.loc[w["aqi"].idxmax(), "ts"],
            "main_pollutant": main,
            "attribution": json.dumps({"zscores": zs_sorted},
                                      ensure_ascii=False, allow_nan=False),
            "model_version": "iforest-c0.01-v1",
        })

ev = pd.DataFrame(events)
print(f"事件数：{len(ev)}（>= {MIN_HOURS} 小时连续异常）")
if len(ev):
    print("主控污染物分布：")
    print(ev["main_pollutant"].value_counts().to_string())
    print("TOP5 事件（按持续时长）：")
    print(ev.nlargest(5, "duration_hours")[
        ["city", "start_time", "duration_hours", "main_pollutant", "peak_pm25"]].to_string(index=False))

with engine.begin() as c:
    c.execute(text("TRUNCATE TABLE anomaly_events"))
if len(ev):
    ev.to_sql("anomaly_events", engine, if_exists="append", index=False)
with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM anomaly_events")).scalar()
print(f"写入完成：anomaly_events {n} 行")
