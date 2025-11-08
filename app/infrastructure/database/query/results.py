from typing import Any, Callable, Mapping, TypeVar, Iterable, Iterator

T = TypeVar("T")


class SingleQueryResult:
    def __init__(self, result: Mapping[str, Any] | None) -> None:
        self._data: dict[str, Any] = dict(result) if result else {}

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def is_empty(self) -> bool:
        return not self._data

    def to_model(
        self, model: Callable[..., T], *, raise_if_empty: bool = False
    ) -> T | None:
        if self.is_empty():
            if raise_if_empty:
                raise ValueError("Cannot convert empty result to model")
            return None
        return model(**self._data)

    def as_dict(self) -> dict[str, Any]:
        return self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SingleQueryResult) and self._data == other._data

    def __repr__(self) -> str:
        return f"<SingleQueryResult {self._data}>"


class MultipleQueryResult:
    def __init__(self, results: Iterable[Mapping[str, Any]] | None = None) -> None:
        self._data: list[dict[str, Any]] = (
            [dict(row) for row in results] if results else []
        )

    @property
    def data(self) -> list[dict[str, Any]]:
        return self._data

    def is_empty(self) -> bool:
        return not self._data

    def to_models(
        self, model: Callable[..., T], *, raise_if_empty: bool = False
    ) -> list[T] | None:
        if self.is_empty():
            if raise_if_empty:
                raise ValueError("Cannot convert empty result to models")
            return None
        return [model(**row) for row in self._data]

    def first(self) -> SingleQueryResult:
        return (
            SingleQueryResult(self._data[0]) if self._data else SingleQueryResult(None)
        )

    def as_dicts(self) -> list[dict[str, Any]]:
        return self._data

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._data)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self._data[idx]

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, MultipleQueryResult) and self._data == other._data

    def __repr__(self) -> str:
        return f"<MultipleQueryResult {len(self._data)} rows>"
