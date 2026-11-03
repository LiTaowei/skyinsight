# -*- coding: utf-8 -*-
"""
全局统一配置：数据库连接、路径与公共常量。

数据处理脚本（data/analysis/*.py）与 Web 应用（app/config.py）都从这里取连接，
保证只有一个权威来源。所有连接参数均可通过环境变量覆盖：

    MYSQL_HOST  数据库主机，默认 localhost（容器组网内用服务名 mysql）
    MYSQL_PORT  端口，默认 3306
    MYSQL_USER  用户名，默认 root
    MYSQL_PASS  密码，默认 123456（生产请务必通过环境变量注入）
    MYSQL_DB    数据库名，默认 air_quality
"""
import os

from sqlalchemy import create_engine

# ---------- 数据库连接参数（全部走环境变量，给开发默认值） ----------
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "123456")
MYSQL_DB = os.environ.get("MYSQL_DB", "air_quality")


def build_url(include_db: bool = True) -> str:
    """构造 SQLAlchemy 连接串；建库阶段 include_db=False 不指定数据库。"""
    db = f"/{MYSQL_DB}" if include_db else ""
    return (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}{db}?charset=utf8mb4"
    )


def get_engine(include_db: bool = True):
    """返回 SQLAlchemy engine；pool_pre_ping 避免长连接失效。"""
    return create_engine(build_url(include_db), pool_pre_ping=True, pool_recycle=3600)


# ---------- 15 项污染物指标（各脚本口径一致，禁止各自维护） ----------
MEASURE = ["aqi", "pm25", "pm25_24h", "pm10", "pm10_24h",
           "so2", "so2_24h", "no2", "no2_24h",
           "o3", "o3_8h", "o3_24h", "o3_8h_24h", "co", "co_24h"]

# ---------- 项目路径 ----------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
OUTPUT_DIR = os.path.join(ANALYSIS_DIR, "output")
SCHEMA_FILE = os.path.join(DATA_DIR, "schema.sql")
