# -*- coding: utf-8 -*-
"""接口 14-15：地图与城市钻取"""
from datetime import date as _date

from fastapi import APIRouter, HTTPException, Query

from .. import queries

router = APIRouter(prefix="/api", tags=["map"])


def _parse(v: str | None, name: str):
    if not v:
        return None
    try:
        return _date.fromisoformat(v)
    except ValueError:
        raise HTTPException(422, f"{name} 需为 YYYY-MM-DD 格式")


@router.get("/map/aqi", summary="⑭ 某时刻 20 城 AQI 地图点（缺省=库内最新时刻）")
def map_aqi(date: str | None = Query(None, description="YYYY-MM-DD"),
            hour: int | None = Query(None, ge=0, le=23)):
    return queries.map_aqi(_parse(date, "date"), hour)


@router.get("/city/{city}/series", summary="⑮ 单城市时间序列（跨度>31 天自动转日均，fields 白名单）")
def city_series(
    city: str,
    start: str | None = Query(None, description="YYYY-MM-DD，缺省=最近 90 天"),
    end: str | None = Query(None, description="YYYY-MM-DD，缺省=库内最新日期"),
    fields: str = Query("aqi,pm25", description="逗号分隔，15 项指标白名单"),
):
    return queries.city_series(
        city, _parse(start, "start"), _parse(end, "end"),
        [f.strip() for f in fields.split(",") if f.strip()])
