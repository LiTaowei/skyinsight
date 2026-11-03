# -*- coding: utf-8 -*-
"""接口 9-13：算法结果（聚类 / PCA 载荷 / 异常检测）"""
from fastapi import APIRouter, Query

from .. import queries

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_BATCH = Query("all", pattern="^(all|winter|summer)$", description="聚类批次：all/winter/summer")


@router.get("/cluster", summary="⑨ 聚类散点（PC1×PC2）+ 簇中心画像")
def cluster(batch: str = _BATCH):
    return queries.cluster_result(batch)


@router.get("/pca-loadings", summary="⑩ PCA 载荷矩阵与方差贡献率（全期口径，首次调用约 3 秒）")
def pca_loadings():
    return queries.pca_loadings()


@router.get("/anomaly/summary", summary="⑪ 异常事件总览（按城市 / 主控污染物 / 时长 TOP10）")
def anomaly_summary():
    return queries.anomaly_summary()


@router.get("/anomaly/events", summary="⑫ 异常事件分页列表（可按城市、最短时长筛选）")
def anomaly_events(
    city: str | None = Query(None, description="城市名"),
    min_hours: int | None = Query(None, ge=1, description="最短持续小时数"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return queries.anomaly_events(city, min_hours, limit, offset)


@router.get("/anomaly/timeline/{city}", summary="⑬ 单城某日 24h 异常分数时间线（date 缺省=最近有数据的一天）")
def anomaly_timeline(city: str, date: str | None = Query(None, description="YYYY-MM-DD")):
    return queries.anomaly_timeline(city, date)
