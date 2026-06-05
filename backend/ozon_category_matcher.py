from __future__ import annotations

import re
from typing import Any


BUCKETS: list[dict[str, Any]] = [
    {
        "bucket": "fashion_accessories",
        "category": "Fashion accessories",
        "keywords": ["头巾", "发带", "发箍", "围巾", "方巾", "腰带", "饰品", "项链", "earring", "scarf"],
        "ozon_phrases": ["аксессуары для волос", "для волос", "головной убор", "шарф", "платок"],
        "ozon_terms": ["accessories", "fashion accessories", "аксессуар", "бижутер"],
        "ozon_negative_terms": [
            "подголовник",
            "бан",
            "электроник",
            "стабилизатор",
            "микроскоп",
            "телескоп",
            "игров",
            "камера",
            "аудио",
            "консол",
            "запчаст",
            "авто",
        ],
    },
    {
        "bucket": "clothing",
        "category": "Clothing",
        "keywords": ["女装", "男装", "上衣", "衬衫", "连衣裙", "裤", "外套", "blouse", "dress"],
        "ozon_terms": ["clothing", "одежда", "блуз", "плать", "брюк", "рубаш"],
    },
    {
        "bucket": "shoes",
        "category": "Shoes",
        "keywords": ["鞋", "凉鞋", "拖鞋", "靴", "sandal", "shoe"],
        "ozon_terms": ["shoes", "обув", "сандал", "ботин"],
    },
    {
        "bucket": "home",
        "category": "Home decor",
        "keywords": ["家居", "收纳", "装饰", "置物", "厨房", "浴室", "home", "storage"],
        "ozon_terms": ["home", "household", "дом", "хранен", "декор", "кухн"],
    },
    {
        "bucket": "garden_diy",
        "category": "Garden and DIY",
        "keywords": ["园艺", "花盆", "喷壶", "工具", "五金", "diy", "garden"],
        "ozon_terms": ["garden", "diy", "сад", "инструмент", "ремонт"],
    },
]


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _score_ozon_candidate(bucket: dict[str, Any], text: str) -> int:
    score = 0
    for phrase in bucket.get("ozon_phrases", []):
        if _text(phrase) in text:
            score += 4
    for term in bucket["ozon_terms"]:
        if _text(term) in text:
            score += 1
    for term in bucket.get("ozon_negative_terms", []):
        if _text(term) in text:
            score -= 3
    return score


def classify_1688_source(source: dict[str, Any]) -> dict[str, Any]:
    text = _text(" ".join(str(source.get(key) or "") for key in ("title", "shop_name", "shopName", "category")))
    best = BUCKETS[-1]
    best_score = 0
    for bucket in BUCKETS:
        score = sum(1 for keyword in bucket["keywords"] if _text(keyword) in text)
        if score > best_score:
            best = bucket
            best_score = score
    if not best_score:
        return {"bucket": "general", "category": "General", "confidence": 0.25}
    confidence = 0.35 + min(best_score, 3) * 0.18 if best_score else 0.25
    return {"bucket": best["bucket"], "category": best["category"], "confidence": round(confidence, 2)}


def flatten_ozon_category_tree(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def walk(nodes: list[dict[str, Any]], parent_name: str = "", parent_category_id: str = "") -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = str(node.get("category_name") or node.get("name") or "").strip()
            category_id = str(
                node.get("description_category_id") or node.get("category_id") or parent_category_id
            ).strip()
            type_id = str(node.get("type_id") or "").strip()
            type_name = str(node.get("type_name") or "").strip()
            if category_id and type_id:
                candidates.append(
                    {
                        "category": type_name or name or parent_name,
                        "categoryId": category_id,
                        "typeId": type_id,
                        "searchText": " ".join(part for part in [parent_name, name, type_name] if part),
                    }
                )
            children = node.get("children")
            if isinstance(children, list):
                walk(children, " / ".join(part for part in [parent_name, name] if part), category_id)

    walk(items)
    return candidates


def match_ozon_category(source: dict[str, Any], candidates: list[dict[str, str]] | None = None) -> dict[str, Any]:
    classified = classify_1688_source(source)
    if classified["bucket"] == "general":
        return {
            "ozon_category": "General",
            "ozon_category_id": "0",
            "ozon_type_id": "0",
            "ozon_category_confidence": classified["confidence"],
            "ozon_category_matched_by": "local_keywords:general",
        }
    bucket = next(item for item in BUCKETS if item["bucket"] == classified["bucket"])
    best_candidate: dict[str, str] | None = None
    best_score = 0
    for candidate in candidates or []:
        text = _text(" ".join(str(candidate.get(key) or "") for key in ("category", "searchText")))
        score = _score_ozon_candidate(bucket, text)
        if score > best_score:
            best_candidate = candidate
            best_score = score
    if best_candidate:
        return {
            "ozon_category": best_candidate["category"],
            "ozon_category_id": best_candidate["categoryId"],
            "ozon_type_id": best_candidate["typeId"],
            "ozon_category_confidence": min(0.95, classified["confidence"] + 0.2),
            "ozon_category_matched_by": f"ozon_tree:{classified['bucket']}",
        }
    return {
        "ozon_category": bucket["category"],
        "ozon_category_id": "0",
        "ozon_type_id": "0",
        "ozon_category_confidence": classified["confidence"],
        "ozon_category_matched_by": f"local_keywords:{classified['bucket']}",
    }
