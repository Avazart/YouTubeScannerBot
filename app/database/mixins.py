from datetime import datetime

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import ColumnProperty, Mapped, mapped_column


class ReprMixin:
    def __repr__(self):
        cls = self.__class__
        mapper = cls.__mapper__  # noqa
        column_attrs = [
            attr.key
            for attr in mapper.attrs
            if isinstance(attr, ColumnProperty)
        ]
        values = ", ".join(
            f"{name}={getattr(self, name)!r}" for name in column_attrs
        )
        return f"{cls.__name__}({values})"


class TimeStampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
    )
