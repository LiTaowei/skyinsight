# -*- coding: utf-8 -*-
"""SQL 查询层：全部接口的 SQL 集中在此。
元数据/统计（接口 1-8）对应 analysis_queries.sql ①~⑥ 的参数化版本；
算法结果与地图钻取（接口 9-15）读第二阶段落库表。"""
import json
from datetime import date, timedelta
from functools import lru_cache

from sqlalchemy import bindparam, text

from .config import MEASURE
from .database import engine


def _rows(sql, params=None):
    with engine.connect() as c:
        return [dict(m) for m in c.execute(text(sql), params or {}).mappings()]


# ---------- 元数据（接口 1-2） ----------

def cities():
    return _rows(
        "SELECT city, province, region, longitude AS lng, latitude AS lat "
        "FROM city_info ORDER BY region, city")


def aqi_levels():
    return _rows(
        "SELECT level_name, `lower`, `upper`, color "
        "FROM aqi_level ORDER BY `lower`")


# ---------- 统计图表（接口 3-8，对应 SQL ①~⑥） ----------

def seasonal(city=None, year=None):  # ① 四季 PM2.5/O3/AQI 均值（city/year 均可选）
    conds, params = [], {}
    if city:
        conds.append("city = :city"); params["city"] = city
    if year:
        conds.append("YEAR(date) = :year"); params["year"] = year
    cond = (" WHERE " + " AND ".join(conds)) if conds else ""
    return _rows(
        "SELECT CASE WHEN MONTH(date) IN (12,1,2) THEN '冬季'"
        " WHEN MONTH(date) IN (3,4,5) THEN '春季'"
        " WHEN MONTH(date) IN (6,7,8) THEN '夏季'"
        " ELSE '秋季' END AS season,"
        " ROUND(AVG(pm25), 1) AS avg_pm25,"
        " ROUND(AVG(o3), 1) AS avg_o3,"
        " ROUND(AVG(aqi), 1) AS avg_aqi"
        " FROM air_quality_detail" + cond +
        " GROUP BY season"
        " ORDER BY FIELD(season, '春季', '夏季', '秋季', '冬季')", params)


_SEASON_MONTHS = {"winter": (12, 1, 2), "summer": (6, 7, 8)}  # 聚类批次 → 季节月份


def hourly(city=None, year=None, season=None):  # ② 0-23 时昼夜曲线（city/year/season 均可选）
    conds, params = [], {}
    if city:
        conds.append("city = :city"); params["city"] = city
    if year:
        conds.append("YEAR(date) = :year"); params["year"] = year
    if season in _SEASON_MONTHS:
        months = ",".join(str(m) for m in _SEASON_MONTHS[season])
        conds.append(f"MONTH(date) IN ({months})")
    cond = (" WHERE " + " AND ".join(conds)) if conds else ""
    return _rows(
        "SELECT hour, ROUND(AVG(pm25), 1) AS avg_pm25,"
        " ROUND(AVG(o3), 1) AS avg_o3, ROUND(AVG(aqi), 1) AS avg_aqi"
        " FROM air_quality_detail" + cond +
        " GROUP BY hour ORDER BY hour", params)


def ranking(year=None):  # ③ 城市 AQI 排行
    cond = " WHERE YEAR(date) = :year" if year else ""
    return _rows(
        "SELECT city, ROUND(AVG(aqi), 1) AS avg_aqi,"
        " ROUND(AVG(pm25), 1) AS avg_pm25, MAX(aqi) AS max_aqi"
        " FROM air_quality_detail" + cond +
        " GROUP BY city ORDER BY avg_aqi DESC",
        {"year": year} if year else None)


_DEFAULT_CITIES = ["北京", "天津", "济南", "郑州"]


def monthly(cities=None):  # ④ 多城市月度 AQI 走势
    if not cities:
        cities = _DEFAULT_CITIES
    stmt = text(
        "SELECT city, DATE_FORMAT(date, '%Y-%m') AS ym,"
        " ROUND(AVG(aqi), 1) AS avg_aqi"
        " FROM air_quality_detail WHERE city IN :cities"
        " GROUP BY city, ym ORDER BY ym, city"
    ).bindparams(bindparam("cities", expanding=True))
    with engine.connect() as c:
        return [dict(m) for m in c.execute(stmt, {"cities": cities}).mappings()]


def good_days(city=None, year=None):  # ⑤ 逐年优良天数（城市×日均 AQI<=100 记 1 个优良日）
    conds, params = ["aqi IS NOT NULL"], {}
    if city:
        conds.append("city = :city"); params["city"] = city
    if year:
        conds.append("YEAR(date) = :year"); params["year"] = year
    cond = " AND ".join(conds)
    # 内层：城市×日均 AQI（简化口径：当日小时 AQI 均值）；中层：城市×年优良天数；外层：不选城 = 20 城年均，选城 = 单城
    return _rows(
        "SELECT yr, ROUND(AVG(good_days), 1) AS good_days,"
        " ROUND(AVG(total_days), 1) AS total_days,"
        " ROUND(100 * SUM(good_days) / SUM(total_days), 1) AS good_ratio_pct"
        " FROM ("
        "  SELECT city, yr, SUM(daily_aqi <= 100) AS good_days, COUNT(*) AS total_days"
        "  FROM ("
        "   SELECT city, date, YEAR(date) AS yr, AVG(aqi) AS daily_aqi"
        "   FROM air_quality_detail WHERE " + cond +
        "   GROUP BY city, date"
        "  ) t GROUP BY city, yr"
        " ) y GROUP BY yr ORDER BY yr", params)


def primary_pollutant(city=None, year=None, season=None):  # ⑥ 首要污染物频次（不含"无"）
    conds, params = ["primary_pollutant IS NOT NULL", "primary_pollutant <> '无'"], {}
    if city:
        conds.append("city = :city"); params["city"] = city
    if year:
        conds.append("YEAR(date) = :year"); params["year"] = year
    if season in _SEASON_MONTHS:
        months = ",".join(str(m) for m in _SEASON_MONTHS[season])
        conds.append(f"MONTH(date) IN ({months})")
    cond = " WHERE " + " AND ".join(conds)
    return _rows(
        "SELECT primary_pollutant AS pollutant, COUNT(*) AS cnt"
        " FROM air_quality_detail" + cond +
        " GROUP BY primary_pollutant ORDER BY cnt DESC", params)


# ---------- 算法结果（接口 9-13） ----------

def cluster_result(batch="all"):  # ⑨ 聚类散点 + 簇中心画像
    points = _rows(
        "SELECT city, cluster_id, cluster_label, pc1, pc2"
        " FROM city_cluster_result WHERE batch = :b"
        " ORDER BY cluster_id, city", {"b": batch})
    centers = _rows(
        "SELECT cluster_id, cluster_label, aqi, pm25, pm10, so2, no2, o3, co"
        " FROM cluster_center WHERE batch = :b ORDER BY cluster_id", {"b": batch})
    return {"batch": batch, "points": points, "centers": centers}


@lru_cache(maxsize=1)
def _pca_model():
    """与 cluster_pca_kmeans.py 全期口径一致：20 城 × 15 指标均值 -> 标准化 -> PCA。
    离线静态数据，lru_cache 后首次 3 秒、后续毫秒级。"""
    import numpy as np
    import pandas as pd
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    df = pd.read_sql(
        "SELECT city, {} FROM air_quality_detail".format(", ".join(MEASURE)), engine)
    profile = df.groupby("city")[MEASURE].mean()
    x = StandardScaler().fit_transform(profile)
    pca = PCA(n_components=0.85).fit(x)
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)  # 相关系数型载荷
    return (list(MEASURE),
            [round(float(v), 4) for v in pca.explained_variance_ratio_],
            [round(float(v), 4) for v in np.cumsum(pca.explained_variance_ratio_)],
            loadings)


def pca_loadings():  # ⑩ 载荷矩阵与方差贡献率
    measures, evr, cum, load = _pca_model()
    n = len(evr)
    return {
        "measures": measures,
        "explained_variance_ratio": evr,
        "cumulative_variance_ratio": cum,
        "loadings": [
            {"measure": m,
             **{"pc{}".format(i + 1): round(float(load[j, i]), 4) for i in range(n)}}
            for j, m in enumerate(measures)
        ],
    }


def anomaly_summary():  # ⑪ 异常事件总览
    base = _rows(
        "SELECT COUNT(*) AS total, ROUND(AVG(duration_hours), 1) AS avg_duration,"
        " MAX(duration_hours) AS max_duration,"
        " ROUND(AVG(peak_aqi), 1) AS avg_peak_aqi"
        " FROM anomaly_events")[0]
    return {
        "total": base["total"],
        "avg_duration": base["avg_duration"],
        "max_duration": base["max_duration"],
        "avg_peak_aqi": base["avg_peak_aqi"],
        "by_city": _rows(
            "SELECT city, COUNT(*) AS cnt FROM anomaly_events"
            " GROUP BY city ORDER BY cnt DESC"),
        "by_pollutant": _rows(
            "SELECT main_pollutant AS pollutant, COUNT(*) AS cnt"
            " FROM anomaly_events WHERE main_pollutant IS NOT NULL"
            " GROUP BY main_pollutant ORDER BY cnt DESC"),
        "top_by_duration": _rows(
            "SELECT city, start_time, end_time, duration_hours,"
            " peak_aqi, peak_pm25, main_pollutant"
            " FROM anomaly_events ORDER BY duration_hours DESC, peak_aqi DESC LIMIT 10"),
    }


def anomaly_events(city=None, min_hours=None, limit=20, offset=0):  # ⑫ 分页列表
    conds, params = [], {}
    if city:
        conds.append("city = :city")
        params["city"] = city
    if min_hours:
        conds.append("duration_hours >= :mh")
        params["mh"] = min_hours
    where = " AND ".join(conds) or "1=1"
    items = _rows(
        "SELECT id, city, start_time, end_time, duration_hours, peak_aqi, peak_pm25,"
        " peak_time, main_pollutant, attribution"
        " FROM anomaly_events WHERE " + where +
        " ORDER BY start_time DESC LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset})
    for it in items:  # pymysql 返回的 JSON 列是字符串，解成对象
        if isinstance(it.get("attribution"), str):
            try:
                it["attribution"] = json.loads(it["attribution"])
            except (ValueError, TypeError):
                pass
    total = _rows(
        "SELECT COUNT(*) AS total FROM anomaly_events WHERE " + where, params)[0]["total"]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


def anomaly_timeline(city, day=None):  # ⑬ 单城某日 24h 分数时间线
    if day is None:
        day = _rows("SELECT MAX(date) AS d FROM anomaly_hourly WHERE city = :c",
                    {"c": city})[0]["d"]
        if day is None:
            return {"city": city, "date": None, "points": []}
    points = _rows(
        "SELECT h.hour, h.score, h.is_anomaly, d.aqi, d.pm25"
        " FROM anomaly_hourly h LEFT JOIN air_quality_detail d"
        " ON d.city = h.city AND d.date = h.date AND d.hour = h.hour"
        " WHERE h.city = :c AND h.date = :dt ORDER BY h.hour",
        {"c": city, "dt": day})
    return {"city": city, "date": str(day), "points": points}


# ---------- 地图与钻取（接口 14-15） ----------

def map_aqi(day=None, hour=None):  # ⑭ 某时刻 20 城 AQI 地图点
    if day is None:
        day = _rows("SELECT MAX(date) AS d FROM air_quality_detail")[0]["d"]
    if hour is None:
        hour = _rows("SELECT MAX(hour) AS h FROM air_quality_detail WHERE date = :d",
                     {"d": day})[0]["h"]
    points = _rows(
        "SELECT d.city, c.region, c.longitude AS lng, c.latitude AS lat,"
        " d.aqi, lv.level_name, lv.color"
        " FROM air_quality_detail d"
        " JOIN city_info c ON c.city = d.city"
        " JOIN aqi_level lv ON d.aqi BETWEEN lv.lower AND lv.upper"
        " WHERE d.date = :d AND d.hour = :h",
        {"d": day, "h": hour})
    return {"date": str(day), "hour": hour, "points": points}


def city_series(city, start=None, end=None, fields=("aqi", "pm25")):  # ⑮ 钻取序列
    flds = [f for f in fields if f in MEASURE] or ["aqi", "pm25"]  # 白名单防注入
    if end is None:
        end = _rows("SELECT MAX(date) AS d FROM air_quality_detail")[0]["d"]
    if start is None:
        start = end - timedelta(days=89)  # 缺省最近 90 天
    if (end - start).days > 31:  # 大跨度自动降采样为日均
        cols = ", ".join("ROUND(AVG({}), 1) AS {}".format(f, f) for f in flds)
        sql = ("SELECT date, {} FROM air_quality_detail"
               " WHERE city = :c AND date BETWEEN :s AND :e"
               " GROUP BY date ORDER BY date").format(cols)
        gran = "daily"
    else:
        sql = ("SELECT date, hour, {} FROM air_quality_detail"
               " WHERE city = :c AND date BETWEEN :s AND :e"
               " ORDER BY date, hour").format(", ".join(flds))
        gran = "hourly"
    points = _rows(sql, {"c": city, "s": start, "e": end})
    return {"city": city, "granularity": gran, "fields": flds,
            "start": str(start), "end": str(end), "points": points}
