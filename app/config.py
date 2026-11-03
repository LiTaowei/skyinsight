# -*- coding: utf-8 -*-
"""全局配置：数据库连接与公共常量（统一收口到 pipeline_common）"""
import os

from pipeline_common import MEASURE, build_url

# 与数据处理脚本共用同一个连接来源（环境变量 MYSQL_HOST/PORT/USER/PASS/DB）
DATABASE_URL = build_url()

# AI 智能解读（DeepSeek 兼容接口）：密钥默认留空，不影响启动；
# 需要 AI 功能时设环境变量 DEEPSEEK_API_KEY 即可
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = float(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
