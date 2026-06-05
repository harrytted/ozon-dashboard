from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceQuote:
    fixed_cost_cny: float
    price_cny: float
    net_profit_cny: float
    fixed_cost_rub: float
    price_rub: float
    net_profit_rub: float
    net_margin: float
    total_fee_rate: float


def calculate_price(
    *,
    cost_cny: float,
    exchange_rate: float,
    commission_rate: float,
    payment_rate: float,
    ad_rate: float,
    return_loss_rate: float,
    target_margin: float,
    fixed_fee_rub: float = 0,
) -> PriceQuote:
    if cost_cny <= 0:
        raise ValueError("成本必须大于 0")
    if exchange_rate <= 0:
        raise ValueError("汇率必须大于 0")
    rates = [commission_rate, payment_rate, ad_rate, return_loss_rate, target_margin]
    if any(rate < 0 for rate in rates):
        raise ValueError("利润率和扣点不能为负数")
    total_fee_rate = commission_rate + payment_rate + ad_rate + return_loss_rate
    denominator = 1 - total_fee_rate - target_margin
    if denominator <= 0:
        raise ValueError("利润率和扣点之和必须小于 1")
    fixed_cost_cny = cost_cny + fixed_fee_rub
    price_cny = fixed_cost_cny / denominator
    variable_fees = price_cny * total_fee_rate
    net_profit_cny = price_cny - variable_fees - fixed_cost_cny
    return PriceQuote(
        fixed_cost_cny=fixed_cost_cny,
        price_cny=price_cny,
        net_profit_cny=net_profit_cny,
        fixed_cost_rub=fixed_cost_cny,
        price_rub=price_cny,
        net_profit_rub=net_profit_cny,
        net_margin=net_profit_cny / price_cny,
        total_fee_rate=total_fee_rate,
    )
