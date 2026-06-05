from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OzonBindRequest(BaseModel):
    name: str = ""
    clientId: str = ""
    apiKey: str = ""


class OzonBulkStoreInput(BaseModel):
    name: str
    clientId: str
    apiKey: str
    owner: str = "真实 API"


class OzonBulkBindRequest(BaseModel):
    stores: list[OzonBulkStoreInput]
    validateWithOzon: bool = False
    autoSyncProducts: bool = False


class Import1688Request(BaseModel):
    urls: list[str] = Field(default_factory=list)


class Rematch1688CategoriesRequest(BaseModel):
    sourceIds: list[str] = Field(default_factory=list)


class NormalizeProductsRequest(BaseModel):
    sourceIds: list[str] = Field(default_factory=list)
    targetMargin: float = 0.30
    exchangeRate: float = 10.5
    domesticShippingCny: float = 1.5
    packagingCny: float = 1.0
    warehouseHandlingCny: float = 1.0
    crossBorderShippingCny: float = 18.0
    bufferCny: float = 1.0
    commissionRate: float = 0.18
    paymentRate: float = 0.015
    adRate: float = 0.05
    returnLossRate: float = 0.03


class PublishProductsRequest(BaseModel):
    productIds: list[str] = Field(default_factory=list)
    storeIds: list[str] = Field(default_factory=list)
    stock: int = 10


class UpdateProductPriceRequest(BaseModel):
    priceCny: float | None = None
    oldPriceCny: float | None = None
    minPriceCny: float | None = None
    priceRub: float | None = None
    oldPriceRub: float | None = None
    minPriceRub: float | None = None


class AiNormalizedProduct(BaseModel):
    ruTitle: str
    description: str
    category: str = "General"
    categoryId: str = "0"
    typeId: str = "0"
    attributes: dict[str, Any] = Field(default_factory=dict)
