from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Mapping, Union

if TYPE_CHECKING:
    from davish.storage import BaseStorage

WSGIResponse = tuple[int, dict[str, str], Union[None, str, bytes]]
WSGIEnviron = Mapping[str, Any]
WSGIStartResponse = Callable[[str, list[tuple[str, str]]], Any]


@dataclass
class Context:
    env: WSGIEnviron
    storage: "BaseStorage"
