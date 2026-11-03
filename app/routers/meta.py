# -*- coding: utf-8 -*-
"""接口 1-2：元数据（城市清单 / AQI 等级配色）"""
from fastapi import APIRouter

from .. import queries

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/cities", summary="城市清单（含经纬度与区域，前端筛选器与地图底座）")
def cities():
    return queries.cities()


@router.get("/meta/aqi-levels", summary="AQI 等级区间与官方配色")
def aqi_levels():
    return queries.aqi_levels()
