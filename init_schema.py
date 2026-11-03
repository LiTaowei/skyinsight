# -*- coding: utf-8 -*-
"""
建库初始化器：用 Python 执行 data/schema.sql（容器内没有 mysql 命令行客户端）。

会先以不指定数据库的方式连接 MySQL，逐条执行 schema.sql 中的语句：
创建数据库、7 张表以及 city_info / aqi_level 字典数据。全部为
IF NOT EXISTS / ON DUPLICATE 口径，幂等可重复执行。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from pipeline_common import SCHEMA_FILE, get_engine


def _split_statements(sql_text: str):
    """去掉 -- 注释行后按分号拆成独立语句，返回非空语句列表。"""
    cleaned = "\n".join(
        line for line in sql_text.splitlines()
        if not re.match(r"^\s*--", line)
    )
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def init_schema():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        statements = _split_statements(f.read())
    # 建库阶段不指定数据库，连接到服务器级
    engine = get_engine(include_db=False)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print(f"建库完成：共执行 {len(statements)} 条语句（库/表/字典数据就绪）")


if __name__ == "__main__":
    init_schema()
