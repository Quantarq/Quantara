"""
Typed helpers for converting Stellar decimal amounts to raw token units.
"""

from decimal import Decimal, ROUND_HALF_UP


def from_stellar_units(amount: Decimal | str, decimals: int) -> int:
    """
    Convert a human Stellar amount into raw integer token units.
    """
    decimal_amount = amount if isinstance(amount, Decimal) else Decimal(amount)
    return int(decimal_amount.scaleb(decimals).quantize(Decimal("1"), ROUND_HALF_UP))


def to_stellar_units(raw_amount: int, decimals: int) -> Decimal:
    """
    Convert raw integer token units into a human Stellar decimal amount.
    """
    return Decimal(raw_amount).scaleb(-decimals)
