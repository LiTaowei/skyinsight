# -*- coding: utf-8 -*-
"""
第三阶段 动作 0：回填 primary_pollutant（首要污染物）
口径经诊断确认（_diagnose_aqi.py 一次性排查）：本数据集的已发布 aqi 与
"六项小时浓度取 IAQI 最大"口径最吻合（中位偏差 0.25，±2 内 80.6%），而非
24h 滑动均值口径（中位偏差 11）。
依据 HJ 633-2012 分段线性插值：
  1. 对 pm25/pm10/so2/no2/co/o3 六项小时浓度分别计算 IAQI
  2. 首要污染物 = IAQI 最大者；max IAQI <= 50（优）记 "无"
  3. 六项输入全缺失的行保持 NULL
连接参数走环境变量（见 pipeline_common.py），写库幂等可重跑。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from sqlalchemy import text

from pipeline_common import get_engine

engine = get_engine()

# HJ 633-2012 表 1：浓度断点与对应 IAQI 级别
# （SO2/NO2/O3/PM 单位 μg/m³，CO 单位 mg/m³；SO2、NO2 的 24h 断点最高只定义到 IAQI 400）
SPECS = {  # 污染物名: (取值列, 浓度断点, IAQI 级别)——全部取小时浓度
    "PM2.5": ("pm25", [0, 35, 75, 115, 150, 250, 350, 500],
              [0, 50, 100, 150, 200, 300, 400, 500]),
    "PM10":  ("pm10", [0, 50, 150, 250, 350, 420, 500, 600],
              [0, 50, 100, 150, 200, 300, 400, 500]),
    "SO2":   ("so2",  [0, 50, 150, 475, 800, 1600, 2620],
              [0, 50, 100, 150, 200, 300, 400]),
    "NO2":   ("no2",  [0, 40, 80, 180, 280, 565, 750],
              [0, 50, 100, 150, 200, 300, 400]),
    "CO":    ("co",   [0, 2, 4, 14, 24, 36, 48, 60],
              [0, 50, 100, 150, 200, 300, 400, 500]),
    "O3":    ("o3",   [0, 160, 200, 300, 400, 800, 1000],
              [0, 50, 100, 150, 200, 300, 400]),
}
# idxmax 平级时按此列序取前者，即隐含优先级
ORDER = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"]


def iaqi(values, breakpoints, levels):
    """分段线性插值计算 IAQI；NaN 输入 -> NaN"""
    v = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    out = np.full(v.shape, np.nan)
    m = ~np.isnan(v)
    out[m] = np.interp(v[m], breakpoints, levels)
    return out


print("读取明细（仅回填所需列）...")
df = pd.read_sql(
    "SELECT id, aqi, pm25, pm10, so2, no2, co, o3 FROM air_quality_detail", engine)
print("行数：", len(df))

iaqis = pd.DataFrame(
    {name: iaqi(df[col], bp, lv) for name, (col, bp, lv) in SPECS.items()})[ORDER]

valid = iaqis.notna().any(axis=1)          # 至少一项可计算
max_iaqi = iaqis.max(axis=1)
arg = iaqis.fillna(-1).idxmax(axis=1)      # 全缺失行占位，下方 ~valid 分支覆盖
pp = pd.Series(np.where(max_iaqi > 50, arg, "无"), index=df.index)
pp[~valid] = None
out = pd.DataFrame({"id": df["id"], "pp": pp})

# ---- 校验：计算出的 max IAQI 应与已发布 aqi 基本一致 ----
chk = pd.DataFrame({"calc": max_iaqi, "pub": df["aqi"]}).dropna()
diff = (chk["calc"] - chk["pub"]).abs()
print(f"与已发布 AQI 一致性：中位偏差 {diff.median():.2f}，|偏差|<=2 占比 "
      f"{(diff <= 2).mean():.1%}，<=5 占比 {(diff <= 5).mean():.1%}")

print("首要污染物分布（计算结果）：")
print(pp.value_counts(dropna=False).to_string())

# ---- 写库：临时表 + JOIN UPDATE ----
t0 = time.time()
with engine.begin() as c:
    c.execute(text("CREATE TEMPORARY TABLE tmp_pp "
                   "(id BIGINT PRIMARY KEY, pp VARCHAR(10))"))
    rows = out.dropna(subset=["pp"]).to_dict("records")  # 全缺失行不写，保持 NULL
    for i in range(0, len(rows), 50000):
        c.execute(text("INSERT INTO tmp_pp (id, pp) VALUES (:id, :pp)"),
                  rows[i:i + 50000])
    c.execute(text("UPDATE air_quality_detail d JOIN tmp_pp t ON d.id = t.id "
                   "SET d.primary_pollutant = t.pp"))
print(f"回填完成，耗时 {time.time() - t0:.1f}s")

with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM air_quality_detail "
                       "WHERE primary_pollutant IS NOT NULL")).scalar()
print(f"落库校验：primary_pollutant 非空 {n} 行 / {len(df)} 行")
