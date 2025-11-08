from typing import Any


class SingleQueryResult:
    """
    Wrapper for a single query result row.
    """

    def __init__(self, result: dict[str, Any] | None):
        self._result = result

    @property
    def exists(self) -> bool:
        """Check if the result exists."""
        return self._result is not None

    @property
    def data(self) -> dict[str, Any] | None:
        """Get the result data."""
        return self._result

    def __repr__(self) -> str:
        return f"SingleQueryResult(exists={self.exists}, data={self._result})"


class MultipleQueryResult:
    """
    Wrapper for multiple query result rows.
    """

    def __init__(self, results: list[dict[str, Any]]):
        self._results = results

    @property
    def exists(self) -> bool:
        """Check if results exist."""
        return len(self._results) > 0

    @property
    def data(self) -> list[dict[str, Any]]:
        """Get all result rows."""
        return self._results

    @property
    def count(self) -> int:
        """Get the number of rows."""
        return len(self._results)

    def __repr__(self) -> str:
        return f"MultipleQueryResult(count={self.count}, data={self._results})"
