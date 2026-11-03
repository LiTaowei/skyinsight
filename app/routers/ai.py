# -*- coding: utf-8 -*-
"""AI 智能解读：方案 A「数据直喂」——把图表背后的结构化数据喂给 DeepSeek 生成分析文字。

设计要点（答辩可讲）：
1. 不训练模型：通用大模型已具备数据分析能力，本模块只做 prompt 工程 + 数据装配；
2. 数字不做视觉识别，而是直接来自 queries 层的真实查询结果，保证解读数值 100% 可信；
3. 模型仅负责"洞察生成"（趋势/对比/异常/成因），不负责数值提取。
"""
import json

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import queries
from ..config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
                      DEEPSEEK_TIMEOUT)

router = APIRouter(prefix="/api/ai", tags=["ai"])

_SYSTEM_PROMPT = (
    "你是空气质量数据分析专家，内嵌在可视化平台的图表卡片中与用户一问一答。规则："
    "1) 只基于系统提供的数据回答，禁止编造数据中不存在的数字；"
    "2) 回答简洁：整体解读用 3-5 条要点，追问用 1-3 句话；"
    "3) 简体中文，不写开场白和总结语；"
    "4) 若问题超出给定数据范围，说明数据中无法回答并给出基于已有数据的合理推测。"
)

# 卡片标识 → (中文标题, 数据装配函数)。数据装配复用 queries 层，与前端图表同源。
def _build_monthly():
    return queries.monthly(["北京", "天津", "济南", "郑州"])

_CARD_BUILDERS = {
    "seasonal": ("四季污染物均值（PM2.5/O3/AQI）",
                 lambda c, y, s: queries.seasonal(c, y)),
    "hourly": ("24 小时昼夜浓度曲线",
               lambda c, y, s: queries.hourly(c, y, s)),
    "gooddays": ("逐年优良天数（城市×日均 AQI<=100 记优良日）",
                 lambda c, y, s: queries.good_days(c)),
    "pp": ("首要污染物频次占比",
           lambda c, y, s: queries.primary_pollutant(c, y, s)),
    "monthly": ("多城市月度 AQI 走势（北京/天津/济南/郑州）",
                lambda c, y, s: _build_monthly()),
    "cluster": ("城市聚类分型（PCA+KMeans，簇画像）",
                lambda c, y, s: queries.cluster_result(s or "all")),
    "anomaly": ("异常事件统计（IsolationForest 检出事件总览）",
                lambda c, y, s: queries.anomaly_summary()),
}

_MAX_HISTORY = 12  # 最多携带最近 12 条历史（约 6 轮），防止 token 膨胀


class ChatMsg(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatReq(BaseModel):
    card: str = Field(..., description="卡片：seasonal/hourly/gooddays/pp/monthly/cluster/anomaly")
    question: str = Field(..., min_length=1, max_length=500, description="用户本轮提问")
    history: list[ChatMsg] = Field(default_factory=list, description="最近对话历史")
    city: str | None = Field(None, description="全局城市筛选（可空=全部）")
    year: int | None = Field(None, description="全局年份筛选（可空=全期）")
    season: str | None = Field(None, description="聚类批次 all/winter/summer")


def _collect_data(req: ChatReq) -> tuple[str, object]:
    entry = _CARD_BUILDERS.get(req.card)
    if not entry:
        raise HTTPException(400, f"未知卡片标识：{req.card}")
    label, builder = entry
    try:
        data = builder(req.city, req.year, req.season)
    except Exception as e:  # 数据装配失败不应暴露堆栈给前端
        raise HTTPException(500, f"数据装配失败：{e}")
    return label, data


async def _chat(messages: list[dict]) -> str:
    if not DEEPSEEK_API_KEY:
        raise HTTPException(503, "未配置 DEEPSEEK_API_KEY，无法使用 AI 解读")
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(504, "大模型响应超时，请稍后重试")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"大模型接口错误 {e.response.status_code}，请检查 API Key")
    except httpx.HTTPError:
        raise HTTPException(502, "无法连接大模型服务（网络问题）")
    return resp.json()["choices"][0]["message"]["content"].strip()


@router.post("/chat", summary="AI 图表一问一答（数据直喂 DeepSeek，每轮重新锚定真实数据）")
async def chat(req: ChatReq):
    label, data = _collect_data(req)
    scope = "，".join(filter(None, [
        f"城市={req.city}" if req.city else None,
        f"年份={req.year}" if req.year else None,
        {"all": "全期", "winter": "冬季", "summer": "夏季"}.get(req.season or "all"),
    ])) or "全部范围"
    system = (
        f"{_SYSTEM_PROMPT}\n\n当前图表：「{label}」，数据范围：{scope}。"
        f"图表背后的真实统计数据（JSON）：\n"
        f"{json.dumps(data, ensure_ascii=False, default=str)}"
    )
    history = [m.model_dump() for m in req.history][-_MAX_HISTORY:]
    text = await _chat([
        {"role": "system", "content": system},
        *history,
        {"role": "user", "content": req.question},
    ])
    return {"card": req.card, "title": label, "text": text}
