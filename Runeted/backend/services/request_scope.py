"""Per-request state via contextvars, for retrofitting a single global
mutable object/dict into something that resolves correctly per
authenticated account without touching every existing call site.

Why this exists: `main.py`'s `current_player` and `services/session.py`'s
`SESSION` were each one process-wide object, read and written directly
by name in hundreds of places. Adding real accounts means each request
must see *its own* account's data, not whatever the last request left
behind — and since Starlette dispatches sync `def` route handlers to a
real threadpool, two requests can genuinely run concurrently, so a
naive "reassign the global at request start" middleware would race:
one thread's in-flight read/write can land against a different
account's data mid-request.

`contextvars.ContextVar` is the standard fix: anyio/Starlette copies
the current context into each dispatched thread, so a value set in
middleware before dispatch is visible only to that request's thread,
with zero cross-request bleed — no rewriting of call sites required.

`ContextObjectProxy` and `ContextDictProxy` forward attribute/item
access to whatever's currently bound in a `ContextVar`, so the existing
name (`current_player`, `SESSION`) keeps working as a drop-in stand-in
for "the real object" everywhere it's already used. Only the places
that *rebind* the name (`current_player = Player()`) need to change, to
call `.set(...)` on the underlying ContextVar instead.
"""
from __future__ import annotations

import contextvars
from typing import Any, Iterator


class ContextObjectProxy:
    """Stands in for a single mutable object. Every attribute get/set
    forwards to whatever object is bound in `ctx` for the current
    request; `__class__`/`__repr__` also forward so isinstance checks
    and debugging output see the real underlying object."""

    def __init__(self, ctx: "contextvars.ContextVar[Any]"):
        object.__setattr__(self, "_ctx", ctx)

    def _target(self) -> Any:
        ctx: contextvars.ContextVar[Any] = object.__getattribute__(self, "_ctx")
        return ctx.get()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target(), name, value)

    def __repr__(self) -> str:
        return repr(self._target())

    @property
    def __class__(self):  # so isinstance(current_player, Player) still works
        return type(self._target())


class ContextDictProxy:
    """Stands in for a single mutable dict. Every item/`.get()`/`in`
    access forwards to whatever dict is bound in `ctx` for the current
    request."""

    def __init__(self, ctx: "contextvars.ContextVar[dict]"):
        self._ctx = ctx

    def _target(self) -> dict:
        return self._ctx.get()

    def __getitem__(self, key: Any) -> Any:
        return self._target()[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._target()[key] = value

    def __delitem__(self, key: Any) -> None:
        del self._target()[key]

    def __contains__(self, key: Any) -> bool:
        return key in self._target()

    def __iter__(self) -> Iterator[Any]:
        return iter(self._target())

    def __len__(self) -> int:
        return len(self._target())

    def get(self, key: Any, default: Any = None) -> Any:
        return self._target().get(key, default)

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._target().update(*args, **kwargs)

    def clear(self) -> None:
        self._target().clear()

    def keys(self):
        return self._target().keys()

    def values(self):
        return self._target().values()

    def items(self):
        return self._target().items()

    def __repr__(self) -> str:
        return repr(self._target())
