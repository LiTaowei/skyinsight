# -*- coding: utf-8 -*-
"""SQLAlchemy engine 单例与连通性检查"""
from sqlalchemy import create_engine, text

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)


def check() -> bool:
    with engine.connect() as c:
        return c.execute(text("SELECT 1")).scalar() == 1
