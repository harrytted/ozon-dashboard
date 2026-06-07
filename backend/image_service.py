from __future__ import annotations

import base64
import email.utils
import hashlib
import hmac
import html
import os
import re
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx

from . import db

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ImageSyncError(RuntimeError):
    pass


def _decode_url(value: str) -> str:
    text = html.unescape(str(value or "")).strip().strip("\"'")
    text = text.replace("\\/", "/")

    def unicode_replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return re.sub(r"\\u([0-9a-fA-F]{4})", unicode_replace, text)


def normalize_image_url(source_url: str, value: str, *, require_image_extension: bool = True) -> str:
    url = _decode_url(value)
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    elif url.startswith("/"):
        url = urljoin(source_url, url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if require_image_extension and not re.search(r"\.(?:jpg|jpeg|png|webp)(?:[?_./-]|$)", parsed.path + ("?" + parsed.query if parsed.query else ""), re.I):
        return ""
    return url


def collect_image_urls(source_url: str, html_text: str = "", manual_urls: list[str] | None = None, limit: int = 8) -> list[str]:
    candidates: list[str] = []
    if manual_urls is not None:
        candidates.extend(manual_urls)
    if html_text:
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'"(?:image|imgUrl|imageUrl|original|bigImageUrl|summImagePath|mainImageUrl|url)"\s*:\s*"([^"]+)"',
            r'["\']((?:https?:)?//[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        ]
        for pattern in patterns:
            candidates.extend(match.group(1) for match in re.finditer(pattern, html_text, flags=re.I | re.S))
    images: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        url = normalize_image_url(source_url, candidate, require_image_extension=manual_urls is None)
        if not url or url in seen:
            continue
        seen.add(url)
        images.append(url)
        if len(images) >= limit:
            break
    return images


def oss_config() -> dict[str, str]:
    config = {
        "endpoint": os.environ.get("ALIYUN_OSS_ENDPOINT", "").strip(),
        "bucket": os.environ.get("ALIYUN_OSS_BUCKET", "").strip(),
        "access_key_id": os.environ.get("ALIYUN_OSS_ACCESS_KEY_ID", "").strip(),
        "access_key_secret": os.environ.get("ALIYUN_OSS_ACCESS_KEY_SECRET", "").strip(),
        "public_base_url": os.environ.get("ALIYUN_OSS_PUBLIC_BASE_URL", "").strip(),
        "prefix": os.environ.get("ALIYUN_OSS_PREFIX", "ozon-products/").strip() or "ozon-products/",
    }
    missing = [key for key in ["endpoint", "bucket", "access_key_id", "access_key_secret", "public_base_url"] if not config[key]]
    if missing:
        raise ImageSyncError(f"缺少阿里云 OSS 配置：{', '.join(missing)}")
    return config


async def download_image(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/125 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://detail.1688.com/",
            },
        )
    if response.status_code >= 400:
        raise ImageSyncError(f"图片下载失败 HTTP {response.status_code}: {url}")
    content_type = str(response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        content_type = _content_type_from_url(url)
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageSyncError(f"不支持的图片格式：{content_type or url}")
    if not response.content:
        raise ImageSyncError(f"图片内容为空：{url}")
    if len(response.content) > 15 * 1024 * 1024:
        raise ImageSyncError(f"图片超过 15MB：{url}")
    return response.content, content_type


def _content_type_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if ".png" in path:
        return "image/png"
    if ".webp" in path:
        return "image/webp"
    if ".jpg" in path or ".jpeg" in path:
        return "image/jpeg"
    return ""


def oss_object_key(config: dict[str, str], offer_id: str, source_id: str, index: int, content_type: str) -> str:
    prefix = config["prefix"].strip("/")
    extension = ALLOWED_IMAGE_TYPES.get(content_type, ".jpg")
    return f"{prefix}/{offer_id}/{source_id}-{index}{extension}"


def _oss_upload_url(config: dict[str, str], object_key: str) -> str:
    endpoint = config["endpoint"].rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    parsed = urlparse(endpoint)
    host = parsed.netloc
    bucket = config["bucket"]
    quoted_key = quote(object_key, safe="/")
    if host.startswith(f"{bucket}."):
        return f"{parsed.scheme}://{host}/{quoted_key}"
    return f"{parsed.scheme}://{bucket}.{host}/{quoted_key}"


def _oss_public_url(config: dict[str, str], object_key: str) -> str:
    return f"{config['public_base_url'].rstrip('/')}/{quote(object_key, safe='/')}"


async def upload_to_oss(image_bytes: bytes, content_type: str, object_key: str) -> str:
    config = oss_config()
    date = email.utils.formatdate(usegmt=True)
    resource = f"/{config['bucket']}/{object_key}"
    string_to_sign = f"PUT\n\n{content_type}\n{date}\n{resource}"
    signature = base64.b64encode(
        hmac.new(config["access_key_secret"].encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    headers = {
        "Authorization": f"OSS {config['access_key_id']}:{signature}",
        "Date": date,
        "Content-Type": content_type,
        "Content-Length": str(len(image_bytes)),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.put(_oss_upload_url(config, object_key), headers=headers, content=image_bytes)
    if response.status_code >= 400:
        raise ImageSyncError(f"OSS 上传失败 HTTP {response.status_code}: {response.text[:300]}")
    return _oss_public_url(config, object_key)


async def upload_image_urls(image_urls: list[str], offer_id: str, source_id: str) -> list[str]:
    config = oss_config()
    uploaded: list[str] = []
    errors: list[str] = []
    for index, url in enumerate(image_urls[:8], start=1):
        try:
            image_bytes, content_type = await download_image(url)
            key = oss_object_key(config, offer_id, source_id, index, content_type)
            uploaded.append(await upload_to_oss(image_bytes, content_type, key))
        except Exception as exc:
            errors.append(str(exc))
    if not uploaded:
        raise ImageSyncError("；".join(errors) or "没有可上传的图片")
    return uploaded


def _decode_uploaded_image(payload: dict[str, Any]) -> tuple[bytes, str]:
    name = str(payload.get("name") or "本地图片")
    data_url = str(payload.get("dataUrl") or payload.get("data") or "").strip()
    content_type = str(payload.get("contentType") or "").split(";", 1)[0].strip().lower()
    if not data_url:
        raise ImageSyncError(f"{name} 内容为空")
    match = re.match(r"^data:([^;,]+);base64,(.+)$", data_url, flags=re.S)
    if match:
        content_type = match.group(1).strip().lower()
        raw_data = match.group(2)
    else:
        raw_data = data_url
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageSyncError(f"{name} 图片格式不支持，仅支持 jpg/png/webp")
    try:
        image_bytes = base64.b64decode(raw_data, validate=True)
    except Exception as exc:
        raise ImageSyncError(f"{name} 不是有效的 base64 图片") from exc
    if not image_bytes:
        raise ImageSyncError(f"{name} 图片内容为空")
    if len(image_bytes) > 15 * 1024 * 1024:
        raise ImageSyncError(f"{name} 图片超过 15MB")
    return image_bytes, content_type


async def upload_source_image_payloads(
    uploaded_images: list[dict[str, Any]],
    offer_id: str,
    source_id: str,
    *,
    start_index: int = 1,
) -> list[str]:
    config = oss_config()
    uploaded: list[str] = []
    errors: list[str] = []
    for offset, payload in enumerate(uploaded_images[:8], start=start_index):
        try:
            image_bytes, content_type = _decode_uploaded_image(payload)
            key = oss_object_key(config, offer_id, source_id, offset, content_type)
            uploaded.append(await upload_to_oss(image_bytes, content_type, key))
        except Exception as exc:
            errors.append(str(exc))
    if uploaded_images and not uploaded:
        raise ImageSyncError("；".join(errors) or "没有可上传的本地图片")
    return uploaded


async def _fetch_source_html(source_url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(
            source_url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
    if response.status_code >= 400:
        raise ImageSyncError(f"1688 返回 HTTP {response.status_code}")
    if "_____tmd_____/punish" in response.text or "x5secdata" in response.text:
        raise ImageSyncError("1688 触发风控验证，未返回商品详情页；请在 1688 页面复制商品图片地址后使用“补图”手动上传")
    return response.text


async def sync_source_images(
    connection: Any,
    source_id: str,
    manual_urls: list[str] | None = None,
) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
    if not row:
        raise ImageSyncError("1688 采集商品不存在")
    source = db.row_to_source(row)
    html_text = "" if manual_urls is not None else await _fetch_source_html(source["url"])
    image_urls = collect_image_urls(source["url"], html_text=html_text, manual_urls=manual_urls)
    if not image_urls:
        raise ImageSyncError("没有找到可上传的商品图片")
    uploaded = await upload_image_urls(image_urls, source["offerId"], source["id"])
    connection.execute(
        """
        UPDATE alibaba_sources
        SET images_json=?, status='parsed', error=''
        WHERE id=?
        """,
        (db.encode_json(uploaded), source_id),
    )
    connection.commit()
    updated = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
    return db.row_to_source(updated)
