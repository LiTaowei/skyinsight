# -*- coding: utf-8 -*-
"""接口 3-8：统计图表（对应 analysis_queries.sql ①~⑥，SQL 见 queries.py）"""
from fastapi import APIRouter, Query

from .. import queries

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/seasonal", summary="① 四季 PM2.5/O3/AQI 均值（city/year 均可选）")
def seasonal(
    city: str | None = Query(None, description="城市名，如：北京"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
):
    return queries.seasonal(city, year)


@router.get("/hourly", summary="② 0-23 时昼夜曲线（city/year/season 均可选，缺省 = 20 城全期均值）")
def hourly(
    city: str | None = Query(None, description="城市名，如：北京"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
    season: str | None = Query(None, description="季节：winter（12-2月）/ summer（6-8月）"),
):
    return queries.hourly(city, year, season)


@router.get("/ranking", summary="③ 城市 AQI 排行（year 缺省 = 全期 2022-2024）")
def ranking(year: int | None = Query(None, ge=2000, le=2100, description="年份")):
    return queries.ranking(year)


@router.get("/monthly", summary="④ 多城市月度 AQI 走势（缺省 = 北方 4 城）")
def monthly(cities: str = Query("北京,天津,济南,郑州", description="城市名，英文逗号分隔")):
    return queries.monthly([c.strip() for c in cities.split(",") if c.strip()])


@router.get("/good-days", summary="⑤ 逐年优良天数（城市×日均 AQI<=100 记优良；city 缺省 = 20 城年均）")
def good_days(
    city: str | None = Query(None, description="城市名，如：北京"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
):
    return queries.good_days(city, year)


@router.get("/primary-pollutant", summary="⑥ 首要污染物频次（city/year/season 均可选，不含“无”）")
def primary_pollutant(
    city: str | None = Query(None, description="城市名，如：石家庄"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
    season: str | None = Query(None, description="季节：winter（12-2月）/ summer（6-8月）"),
):
    return queries.primary_pollutant(city, year, season)
