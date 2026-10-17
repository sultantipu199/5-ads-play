"""Multi-currency normalization and FX conversion."""

from __future__ import annotations

from decimal import Decimal

# Static reference rates relative to USD (production should read from ECB/OpenExchangeRates)
DEFAULT_FX_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "SAR": Decimal("3.75"),  # Saudi Riyal
    "AED": Decimal("3.6725"),  # UAE Dirham
    "EUR": Decimal("0.92"),
    "GBP": Decimal("0.78"),
}


class CurrencyConverter:
    """Converts original platform currencies into the client reporting currency."""

    def __init__(self, rates: dict[str, Decimal] | None = None) -> None:
        self.rates = dict(DEFAULT_FX_RATES)
        if rates:
            self.rates.update(rates)

    def get_fx_rate(self, from_currency: str, to_currency: str) -> Decimal:
        from_cur = from_currency.upper()
        to_cur = to_currency.upper()

        if from_cur == to_cur:
            return Decimal("1.0")

        if from_cur not in self.rates:
            raise ValueError(f"Unknown source currency: {from_cur}")
        if to_cur not in self.rates:
            raise ValueError(f"Unknown target reporting currency: {to_cur}")

        # Base is USD
        usd_rate_from = self.rates[from_cur]
        usd_rate_to = self.rates[to_cur]

        # rate = (amount / usd_rate_from) * usd_rate_to
        rate = usd_rate_to / usd_rate_from
        return rate.quantize(Decimal("0.0001"))
