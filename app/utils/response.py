from app.schemas.common_schema import Page


def page_response(total: int, page: int, size: int, items: list) -> Page:
    return Page(total=total, page=page, size=size, items=items)
