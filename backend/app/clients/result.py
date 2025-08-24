from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, Any, Callable

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    ok: bool
    value: T | None = None
    error: str | None = None
    status_code: int | None = None
    raw: Any | None = None

    def map(self, fn: Callable[[T], T]) -> 'Result[T]':
        if not self.ok or self.value is None:
            return self
        try:
            return success(fn(self.value))
        except Exception as e:  # pragma: no cover
            return failure(str(e))

def success(val: T, *, raw: Any | None = None, status_code: int | None = 200) -> Result[T]:
    return Result(ok=True, value=val, status_code=status_code, raw=raw)

def failure(msg: str, *, status_code: int | None = None, raw: Any | None = None) -> Result[Any]:
    return Result(ok=False, error=msg, status_code=status_code, raw=raw)

__all__ = ['Result','success','failure']
