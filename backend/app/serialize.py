"""Turn a database row into a JSON-friendly dict."""


def to_dict(row, skip: tuple[str, ...] = ("file_data", "password_hash")) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in skip}
