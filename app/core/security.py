from secrets import compare_digest


def verify_plain_password(plain_password: str, stored_password: str) -> bool:
    return compare_digest(plain_password, stored_password)
