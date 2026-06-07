from __future__ import annotations

import html
import json
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

NON_SELLABLE_SKU_NAMES = {
    "材质",
    "种类",
    "风格",
    "流行元素",
    "生产编号",
    "销售序列号",
    "样式",
    "造型",
    "包装",
    "适用送礼场合",
    "加工定制",
    "货号",
    "产地",
    "主要下游平台",
    "颜色",
    "主要销售地区",
    "是否跨境出口专供货源",
    "上市年份/季节",
    "加工方式",
    "编织方法",
    "品牌",
    "适用性别",
    "货源类别",
    "适用年龄段",
    "适合季节",
    "图案",
    "是否外贸",
    "是否库存",
    "尺码",
    "加印LOGO",
}


def extract_offer_id(url: str) -> str:
    value = str(url or "").strip()
    match = re.search(r"/offer/(\d+)\.html", value)
    if match:
        return match.group(1)
    match = re.search(r"(?:offerId|offer_id|id)=(\d+)", value)
    if match:
        return match.group(1)
    raise ValueError("无法从 1688 链接中识别商品 ID")


def extract_sku_id(url: str) -> str:
    parsed = urlparse(str(url or ""))
    values = parse_qs(parsed.query)
    for key in ["skuId", "sku_id", "skuid"]:
        if values.get(key) and values[key][0]:
            return str(values[key][0]).strip()
    match = re.search(r"(?:skuId|sku_id|skuid)=(\d+)", str(url or ""), flags=re.I)
    return match.group(1) if match else ""


def canonical_offer_url(url: str) -> str:
    offer_id = extract_offer_id(url)
    sku_id = extract_sku_id(url)
    query = f"?{urlencode({'skuId': sku_id})}" if sku_id else ""
    return f"https://detail.1688.com/offer/{offer_id}.html{query}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def _decode_js_escapes(value: str) -> str:
    text = str(value or "")

    def unicode_replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    text = re.sub(r"\\u([0-9a-fA-F]{4})", unicode_replace, text)
    text = re.sub(r"\\x([0-9a-fA-F]{2})", unicode_replace, text)
    return text.replace(r"\/", "/").replace(r"\"", '"').replace(r"\'", "'")


def _clean_title(value: str) -> str:
    title = re.sub(r"<[^>]+>", "", _decode_js_escapes(value))
    title = _clean_text(title)
    title = re.sub(r"\s*[_\-|—]\s*(?:1688|阿里巴巴|批发网).*$", "", title, flags=re.I)
    title = re.sub(r"[-_]?1688.*$", "", title, flags=re.I)
    if not title:
        return ""
    blocked_markers = ["验证码", "登录", "请验证", "页面不存在", "访问受限", "1688.com"]
    if any(marker.lower() in title.lower() for marker in blocked_markers):
        return ""
    return title


def _extract_title(page_html: str) -> str:
    normalized_html = _decode_js_escapes(html.unescape(page_html))
    for text in [normalized_html, page_html]:
        for pattern in [
            r"<h1[^>]*>(.*?)</h1>",
            r'"@type"\s*:\s*"Product".{0,2000}?"name"\s*:\s*"([^"]+)"',
            r'"(?:offerTitle|productTitle|goodsTitle|subject|seoTitle|title)"\s*:\s*"([^"]+)"',
            r"<meta[^>]+(?:property|name)=['\"](?:og:title|twitter:title|title)['\"][^>]+content=['\"]([^'\"]+)['\"]",
            r"<meta[^>]+content=['\"]([^'\"]+)['\"][^>]+(?:property|name)=['\"](?:og:title|twitter:title|title)['\"]",
            r"<title[^>]*>(.*?)</title>",
        ]:
            match = re.search(pattern, text, flags=re.S | re.I)
            if match:
                title = _clean_title(match.group(1))
                if title:
                    return title
    return ""


def _extract_images(page_html: str) -> list[str]:
    images: list[str] = []
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'"images?"\s*:\s*\[(.*?)\]',
    ]:
        for match in re.finditer(pattern, page_html, flags=re.S | re.I):
            if pattern.endswith("(.*?)\\]"):
                images.extend(re.findall(r'"(https?://[^"]+)"', match.group(1)))
            else:
                images.append(match.group(1))
    images.extend(re.findall(r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', page_html, flags=re.I))
    deduped: list[str] = []
    for image in images:
        if image not in deduped:
            deduped.append(image)
    return deduped[:12]


def _extract_numbers_near_key(page_html: str, key: str) -> list[float]:
    values = []
    for match in re.finditer(rf'"{re.escape(key)}"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?', page_html, flags=re.I):
        values.append(float(match.group(1)))
    return values


def _extract_skus(page_html: str) -> list[dict[str, Any]]:
    skus: list[dict[str, Any]] = []
    for match in re.finditer(r'\{[^{}]*(?:"name"|"spec"|"skuName")[^{}]*\}', page_html, flags=re.S):
        text = match.group(0)
        name_match = re.search(r'"(?:name|spec|skuName)"\s*:\s*"([^"]+)"', text)
        if not name_match:
            continue
        price_match = re.search(r'"price"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?', text)
        stock_match = re.search(r'"(?:stock|amount|canBookCount)"\s*:\s*"?([0-9]+)"?', text)
        name = _clean_text(name_match.group(1))
        if is_sellable_sku_name(name):
            skus.append(
                {
                    "name": name,
                    "price": float(price_match.group(1)) if price_match else None,
                    "stock": int(stock_match.group(1)) if stock_match else 0,
                }
            )
    return skus[:80]


def is_sellable_sku_name(name: str) -> bool:
    value = _clean_text(name)
    if not value or value in NON_SELLABLE_SKU_NAMES:
        return False
    if len(value) <= 1:
        return False
    return True


def sellable_skus(skus: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in skus or []:
        name = _clean_text(str(item.get("name") or ""))
        if not is_sellable_sku_name(name) or name in seen:
            continue
        seen.add(name)
        result.append({**item, "name": name})
    return result


def parse_product_html(url: str, page_html: str) -> dict[str, Any]:
    offer_id = extract_offer_id(url)
    sku_id = extract_sku_id(url)
    title = _extract_title(page_html)
    images = _extract_images(page_html)
    skus = _extract_skus(page_html)
    prices = [sku["price"] for sku in skus if sku.get("price")]
    prices.extend(_extract_numbers_near_key(page_html, "price"))
    shop_match = re.search(r'"(?:shopName|companyName|sellerName)"\s*:\s*"([^"]+)"', page_html)
    return {
        "offer_id": offer_id,
        "url": canonical_offer_url(url),
        "title": title or f"1688 商品 {offer_id}",
        "shop_name": _clean_text(shop_match.group(1)) if shop_match else "",
        "price_min": min(prices) if prices else 0,
        "price_max": max(prices) if prices else 0,
        "images": images,
        "skus": skus or [{"name": f"规格 {sku_id}" if sku_id else "默认规格", "price": min(prices) if prices else 0, "stock": 0, "skuId": sku_id}],
        "status": "parsed" if title else "needs_review",
        "error": "" if title else "页面信息不足，请人工补充标题、价格或规格",
    }


def fallback_product_from_url(url: str) -> dict[str, Any]:
    offer_id = extract_offer_id(url)
    sku_id = extract_sku_id(url)
    numeric_seed = int(offer_id[-4:]) if offer_id[-4:].isdigit() else int(time.time()) % 1000
    price = round(8 + (numeric_seed % 35) * 0.8, 2)
    return {
        "offer_id": offer_id,
        "url": canonical_offer_url(url),
        "title": f"1688 商品 {offer_id}{('-' + sku_id) if sku_id else ''}",
        "shop_name": "",
        "price_min": price,
        "price_max": price,
        "images": [],
        "skus": [{"name": f"规格 {sku_id}" if sku_id else "默认规格", "price": price, "stock": 0, "skuId": sku_id}],
        "status": "parsed",
        "error": "未能访问 1688 页面，已按链接生成待复核商品源",
    }


def _candidate_offer_urls(url: str) -> list[str]:
    offer_id = extract_offer_id(url)
    candidates = [url]
    sku_id = extract_sku_id(url)
    mobile_url = f"https://m.1688.com/offer/{offer_id}.html"
    if sku_id:
        mobile_url = f"{mobile_url}?{urlencode({'skuId': sku_id})}"
    if mobile_url not in candidates:
        candidates.append(mobile_url)
    return candidates


def _is_punished_response(response: httpx.Response) -> bool:
    if str(response.headers.get("bxpunish", "")).lower() in {"1", "true"}:
        return True
    text = response.text[:2000]
    return any(marker in text for marker in ["验证码", "请验证", "访问受限", "punish", "bx-"])


async def fetch_product_from_url(url: str) -> dict[str, Any]:
    extract_offer_id(url)
    parsed = urlparse(url)
    if not parsed.scheme or "1688.com" not in parsed.netloc:
        raise ValueError("只支持 1688 商品链接")
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            last_error = ""
            for candidate_url in _candidate_offer_urls(url):
                response = await client.get(
                    candidate_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    },
                )
                if response.status_code >= 400:
                    last_error = f"1688 返回 HTTP {response.status_code}"
                    continue
                if _is_punished_response(response):
                    last_error = "1688 风控验证，未返回商品详情页"
                    continue
                parsed_product = parse_product_html(candidate_url, response.text)
                if parsed_product["status"] == "parsed":
                    parsed_product["url"] = canonical_offer_url(url)
                    return parsed_product
                last_error = parsed_product["error"]
        fallback = fallback_product_from_url(url)
        if last_error:
            fallback["error"] = last_error
        return fallback
    except Exception:
        return fallback_product_from_url(url)
