from __future__ import annotations

import hashlib
import json
import re
from typing import Any

OZON_SKU_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def safe_segment(value: str, max_length: int = 18) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").upper()).strip("-")
    return (normalized or "SKU")[:max_length].strip("-") or "SKU"


def stable_spec_hash(spec: dict[str, Any] | list[Any] | str | None) -> str:
    encoded = json.dumps(spec or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:8].upper()


def ozon_sku_suffix(value: str, length: int = 16) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).digest()
    number = int.from_bytes(digest, "big")
    chars: list[str] = []
    while number and len(chars) < length:
        number, remainder = divmod(number, len(OZON_SKU_ALPHABET))
        chars.append(OZON_SKU_ALPHABET[remainder])
    return "".join(chars).ljust(length, "0")[:length]


def generate_offer_id(store_name: str, source_offer_id: str, spec: dict[str, Any] | list[Any] | str | None) -> str:
    encoded = json.dumps(
        {
            "store": str(store_name or ""),
            "source": str(source_offer_id or ""),
            "spec": spec or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"xh{ozon_sku_suffix(encoded)}"
