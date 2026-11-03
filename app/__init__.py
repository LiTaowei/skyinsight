# -*- coding: utf-8 -*-
"""第三阶段 动作 1：FastAPI 应用工厂（骨架）
动作 2-5 逐步填充 routers；动作 6 建立 frontend/ 目录后自动挂载静态页。
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import database
from .routers import ai, analysis, mapview, meta, stats


def create_app() -> FastAPI:
    app = FastAPI(
        title="城市空气质量分析系统",
        version="1.0.0",
        description="第三阶段 Web 可视化接口（共 15 个：元数据 2 / 统计 6 / 算法 5 / 地图 2）",
    )

    @app.get("/api/health", tags=["system"], summary="健康检查（含数据库连通性）")
    def health():
        try:
            db_ok = database.check()
        except Exception:
            db_ok = False
        return {"status": "ok" if db_ok else "db-down", "db": db_ok}

    for r in (meta.router, stats.router, analysis.router, mapview.router,
              ai.router):
        app.include_router(r)

    # 前端静态页：动作 6 建 frontend/ 目录后自动生效（同端口，免 CORS）
    # no-cache：浏览器每次都带 etag 校验（命中则 304），彻底避免改了 JS 前端不生效
    fe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "frontend")
    if os.path.isdir(fe):

        class NoCacheStaticFiles(StaticFiles):
            async def get_response(self, path, scope):
                resp = await super().get_response(path, scope)
                resp.headers["Cache-Control"] = "no-cache"
                return resp

        app.mount("/", NoCacheStaticFiles(directory=fe, html=True),
                  name="frontend")
    return app
