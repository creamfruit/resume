from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, ClassVar


class ModelBase:
    _table: ClassVar[str] = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]):
        if row is None:
            return None
        kwargs = {field: row.get(field) for field in cls.__annotations__.keys()}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in self.__annotations__.keys()}
