from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status


def parse_date_filter(value: str, field_name: str) -> date:
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "INVALID_DATE",
            "message": f"{field_name} must be YYYYMMDD or YYYY-MM-DD.",
        },
    )


def datetime_range(
    from_value: str | None,
    to_value: str | None,
    from_field: str,
    to_field: str,
) -> tuple[datetime | None, datetime | None]:
    start = datetime.combine(parse_date_filter(from_value, from_field), time.min) if from_value else None
    end = None
    if to_value:
        end_date = parse_date_filter(to_value, to_field) + timedelta(days=1)
        end = datetime.combine(end_date, time.min)
    _validate_range(start.date() if start else None, (end - timedelta(days=1)).date() if end else None)
    return start, end


def date_range(
    from_value: str | None,
    to_value: str | None,
    from_field: str,
    to_field: str,
) -> tuple[date | None, date | None]:
    start = parse_date_filter(from_value, from_field) if from_value else None
    end = parse_date_filter(to_value, to_field) if to_value else None
    _validate_range(start, end)
    return start, end


def _validate_range(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_DATE_RANGE",
                "message": "from date must be earlier than or equal to to date.",
            },
        )
