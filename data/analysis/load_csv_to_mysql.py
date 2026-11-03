# -*- coding: utf-8 -*-
"""
数据导入脚本：把 data/raw 下的原始 CSV（quotsoft.net 下载）解析后写入 MySQL。

输入：data/raw/**/china_cities_YYYYMMDD.csv（宽表：date,hour,type,各城市列）
输出：air_quality_detail（长表，20 城 × 小时 × 15 指标）
特性：逐文件处理、分批写入、INSERT ... ON DUPLICATE KEY UPDATE 幂等可重跑

运行前提：
  1. 已执行 data/schema.sql 建库建表（或由 run_pipeline.py 自动完成）
  2. 连接参数统一走环境变量，见 pipeline_common.py（MYSQL_HOST/PORT/USER/PASS/DB）
"""
import glob
import os
import sys
import time

# 允许直接 `python data/analysis/load_csv_to_mysql.py` 运行时导入项目根模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import pandas as pd
from sqlalchemy import text

from pipeline_common import RAW_DIR, get_engine

# 本项目采集的 20 个城市（与 data/schema.sql 的 city_info 一致）
TARGET_CITIES = ["上海", "乌鲁木齐", "北京", "南京", "哈尔滨", "天津", "广州",
                 "成都", "昆明", "杭州", "武汉", "沈阳", "济南", "深圳", "苏州",
                 "西安", "郑州", "重庆", "长沙", "青岛"]

# 原始 type 名 -> 数据库列名
TYPE_MAP = {
    "AQI": "aqi",
    "PM2.5": "pm25", "PM2.5_24h": "pm25_24h",
    "PM10": "pm10", "PM10_24h": "pm10_24h",
    "SO2": "so2", "SO2_24h": "so2_24h",
    "NO2": "no2", "NO2_24h": "no2_24h",
    "O3": "o3", "O3_8h": "o3_8h", "O3_24h": "o3_24h",
    "O3_8h_24h": "o3_8h_24h",
    "CO": "co", "CO_24h": "co_24h",
}

INSERT_SQL = text("""
INSERT INTO air_quality_detail
  (date, hour, city, aqi, pm25, pm25_24h, pm10, pm10_24h,
   so2, so2_24h, no2, no2_24h, o3, o3_8h, o3_24h, o3_8h_24h, co, co_24h)
VALUES
  (:date, :hour, :city, :aqi, :pm25, :pm25_24h, :pm10, :pm10_24h,
   :so2, :so2_24h, :no2, :no2_24h, :o3, :o3_8h, :o3_24h, :o3_8h_24h,
   :co, :co_24h)
ON DUPLICATE KEY UPDATE
  aqi=VALUES(aqi), pm25=VALUES(pm25), pm25_24h=VALUES(pm25_24h),
  pm10=VALUES(pm10), pm10_24h=VALUES(pm10_24h), so2=VALUES(so2),
  so2_24h=VALUES(so2_24h), no2=VALUES(no2), no2_24h=VALUES(no2_24h),
  o3=VALUES(o3), o3_8h=VALUES(o3_8h), o3_24h=VALUES(o3_24h),
  o3_8h_24h=VALUES(o3_8h_24h), co=VALUES(co), co_24h=VALUES(co_24h)
""")

COLS = ["aqi", "pm25", "pm25_24h", "pm10", "pm10_24h", "so2", "so2_24h",
        "no2", "no2_24h", "o3", "o3_8h", "o3_24h", "o3_8h_24h", "co", "co_24h"]


def parse_file(path: str) -> pd.DataFrame:
    """单个宽表 CSV -> 长表 DataFrame（仅 20 城）"""
    df = pd.read_csv(path)
    available = [c for c in TARGET_CITIES if c in df.columns]
    # 宽转长：每个城市一列融化成 city/value
    long = df.melt(id_vars=["date", "hour", "type"], value_vars=available,
                   var_name="city", value_name="value")
    # 同一 (date,hour,city) 下按 type 展开成指标列
    wide = long.pivot_table(index=["date", "hour", "city"], columns="type",
                            values="value", aggfunc="first").reset_index()
    wide.rename(columns={k: v for k, v in TYPE_MAP.items() if k in wide.columns},
                inplace=True)
    for c in COLS:
        if c not in wide.columns:
            wide[c] = None
    wide["date"] = pd.to_datetime(wide["date"].astype(str), format="%Y%m%d").dt.date
    return wide[["date", "hour", "city"] + COLS]


def main():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "**", "china_cities_*.csv"),
                             recursive=True))
    if not files:
        raise SystemExit(
            f"未在 {RAW_DIR} 找到 china_cities_*.csv，请先到 "
            "https://quotsoft.net/air/ 下载数据并按目录结构放回 data/raw")
    print(f"发现 {len(files)} 个原始 CSV，开始解析入库...")
    engine = get_engine()
    total = 0
    t0 = time.time()
    for i, f in enumerate(files, 1):
        part = parse_file(f)
        # pandas 3 中需先转 object 再替换，NaN 才能真正变成 None 传给 pymysql
        part = part.astype(object).where(pd.notna(part), None)
        records = part.to_dict("records")
        with engine.begin() as conn:
            for j in range(0, len(records), 5000):
                conn.execute(INSERT_SQL, records[j:j + 5000])
        total += len(records)
        if i % 50 == 0 or i == len(files):
            print(f"  进度 {i}/{len(files)}，累计写入 {total} 行，"
                  f"用时 {time.time() - t0:.0f}s")
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM air_quality_detail")).scalar()
    print(f"导入完成：本次处理 {total} 行，表内现有 {n} 行")


if __name__ == "__main__":
    main()
