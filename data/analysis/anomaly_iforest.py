# -*- coding: utf-8 -*-
"""
子系统四（上）：孤立森林异常检测，填充 anomaly_hourly
  特征 = 15 污染指标（缺失用列中位数填充）+ hour + weekday + month
  IsolationForest(contamination=0.01) -> score（越小越异常）+ is_anomaly(0/1)
  分数明细落表的意义：前端画分数时间线；调阈值只 UPDATE is_anomaly，无需重跑模型
连接参数走环境变量（见 pipeline_common.py）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from sqlalchemy import text
from sklearn.ensemble import IsolationForest

from pipeline_common import MEASURE, get_engine

engine = get_engine()
VERSION = "iforest-c0.01-v1"

print("读取 MySQL 明细...")
df = pd.read_sql(
    "SELECT city, date, hour, {} FROM air_quality_detail".format(",".join(MEASURE)),
    engine)
print("明细行数：", len(df))

# 时间特征
df["date"] = pd.to_datetime(df["date"])
df["weekday"] = df["date"].dt.weekday
df["month"] = df["date"].dt.month

FEATURES = MEASURE + ["hour", "weekday", "month"]
X = df[FEATURES].copy()
X[MEASURE] = X[MEASURE].fillna(X[MEASURE].median())   # 指标缺失 -> 中位数
print("特征 NaN 剩余：", int(X.isna().sum().sum()))

model = IsolationForest(n_estimators=200, contamination=0.01,
                        random_state=42, n_jobs=-1)
labels = model.fit_predict(X)                 # -1=异常, 1=正常
score = model.score_samples(X)                # 越小越异常

out = pd.DataFrame({
    "city": df["city"],
    "date": df["date"].dt.date,
    "hour": df["hour"],
    "score": np.round(score, 4),
    "is_anomaly": (labels == -1).astype(int),
    "model_version": VERSION,
})
n_anom = int(out["is_anomaly"].sum())
print(f"异常小时数：{n_anom}（contamination=0.01，约 {n_anom/len(out):.2%}）")
print("异常分布 TOP5 城市：")
print(out[out.is_anomaly == 1]["city"].value_counts().head(5).to_string())

with engine.begin() as c:
    c.execute(text("TRUNCATE TABLE anomaly_hourly"))
out.to_sql("anomaly_hourly", engine, if_exists="append", index=False, chunksize=5000)

with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM anomaly_hourly")).scalar()
print(f"写入完成：anomaly_hourly {n} 行")
