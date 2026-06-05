from __future__ import annotations

import os
from typing import Any

import httpx

from .models import AiNormalizedProduct


def heuristic_ru_title(title: str) -> str:
    value = title.strip()
    if any(word in value for word in ["头巾", "发带", "发箍", "头套", "头饰"]):
        return "Женская повязка на голову для волос"
    if any(word in value for word in ["方巾", "围巾", "丝巾", "披肩"]):
        return "Женский платок с принтом"
    if any(word in value for word in ["凉鞋", "拖鞋"]):
        return "Женские летние сандалии"
    if any(word in value for word in ["衬衫", "上衣", "女装"]):
        return "Женская блузка"
    return value if value and not any("\u4e00" <= char <= "\u9fff" for char in value) else "Товар с 1688"


def heuristic_normalize(title: str, source: dict[str, Any] | None = None) -> AiNormalizedProduct:
    value = title.strip() or "1688 product"
    lower = value.lower()
    if any(word in value for word in ["方巾", "头巾", "围巾", "项链", "腰带", "饰品"]):
        category = "Fashion accessories"
    elif any(word in value for word in ["园艺", "花", "工具", "喷壶"]):
        category = "Garden and DIY"
    elif any(word in value for word in ["家居", "收纳", "装饰"]):
        category = "Home decor"
    elif "diy" in lower:
        category = "DIY kits"
    else:
        category = "General"
    return AiNormalizedProduct(
        ruTitle=heuristic_ru_title(value),
        description=f"Товар для продажи на Ozon. Исходное название 1688: {value}.",
        category=category,
        categoryId="0",
        typeId="0",
        attributes={"source": "1688", "category_guess": category},
    )


async def normalize_with_ai(title: str, source: dict[str, Any] | None = None) -> AiNormalizedProduct:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OZON_DASHBOARD_AI_KEY")
    base_url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OZON_DASHBOARD_AI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    if not api_key:
        return heuristic_normalize(title, source)
    prompt = (
        "Convert this 1688 product to Ozon Russian listing fields. "
        "Return compact JSON with ruTitle, description, category, categoryId, typeId, attributes.\n"
        f"Title: {title}\nSource: {source or {}}"
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return AiNormalizedProduct.model_validate_json(content)
    except Exception:
        return heuristic_normalize(title, source)
