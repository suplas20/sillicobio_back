from datetime import date, datetime
from decimal import Decimal
from typing import Any


def yyyymmdd(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y%m%d")


def number(value: Decimal | int | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def clean_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}
