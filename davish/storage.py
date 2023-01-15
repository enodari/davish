import dataclasses
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Iterable, Optional


class Tag(Enum):
    ADDRESS_BOOK = "VADDRESSBOOK"
    CALENDAR = "VCALENDAR"


class ItemTag(Enum):
    VCARD = "VCARD"
    VEVENT = "VEVENT"


@dataclass
class Collection:
    slug: str
    name: str
    tag: Optional[Tag] = None

    @property
    def is_principal(self) -> bool:
        return bool(self.slug)

    @property
    def is_address_book(self) -> bool:
        return self.tag == Tag.ADDRESS_BOOK

    @property
    def is_calendar(self) -> bool:
        return self.tag == Tag.CALENDAR


@dataclass
class Item:
    tag: ItemTag
    href: str
    collection: Collection
    last_modified: datetime


class BaseStorage:
    user: str = "anon"

    def collection_list(self) -> list[Collection]:
        raise NotImplementedError

    def collection_get(
        self,
        slug: str,
    ) -> Optional[Collection]:
        raise NotImplementedError

    def collection_items(
        self,
        collection: Collection,
    ) -> list[Item]:
        raise NotImplementedError

    def item_get(
        self,
        href: str,
        collection: Collection,
    ) -> Optional[Item]:
        raise NotImplementedError

    def item_serialize(self, item: Item) -> str:
        raise NotImplementedError

    def item_time_range(self, item: Item) -> tuple[int, int]:
        raise NotImplementedError

    def item_upload(
        self,
        href: str,
        collection: Collection,
        content: str,
    ) -> Optional[Item]:
        raise NotImplementedError

    def item_delete(
        self,
        item: Item,
    ) -> None:
        raise NotImplementedError

    # Implemented methods, can be overrided if needed

    def user_get(self) -> str:
        return self.user

    def get(
        self,
        path: str,
        depth: str = "0",
    ) -> Collection | Item | None:
        items = list(self.discover_iter(path, depth))
        if len(items):
            return items[0]
        return None

    def discover(
        self,
        path: str,
        depth: str = "0",
    ) -> list[Collection | Item]:
        return list(self.discover_iter(path, depth))

    def discover_iter(
        self,
        path: str,
        depth: str = "0",
    ) -> Iterable[Collection | Item]:
        path = path.strip("/")

        if path == "":
            collection = Collection(slug=path, name="")
            sub_collections = [Collection(slug=self.user, name="")]

        elif path == self.user:
            collection = Collection(slug=self.user, name="")
            sub_collections = self.collection_list()

        else:
            collection = self.collection_get(path)
            if collection:
                sub_collections = self.collection_items(collection)
            else:
                sub_collections = []

        if not collection:
            item = self.item_get_from_path(path)
            if item:
                yield item
            return

        yield collection

        if depth == "0":
            return

        for item in self.collection_items(collection):
            yield item

        for sub_collection in sub_collections:
            yield sub_collection

        return []

    def get_last_modified(self, item: Item | Collection) -> str:
        if isinstance(item, Item):
            last_modified = item.last_modified
        else:
            collection = item
            items_last_modified = [
                i.last_modified for i in self.collection_items(collection)
            ]
            last_modified = max(items_last_modified or [datetime.now()])

        return format_datetime(last_modified)

    def collection_etag(self, collection: Collection) -> str:
        etag = sha256()
        for item in self.collection_items(collection):
            etag.update((item.href + "/" + self.item_etag(item)).encode())
        etag.update(str(dataclasses.asdict(collection)).encode())
        return '"%s"' % etag.hexdigest()

    def item_etag(self, item: Item) -> str:
        etag = sha256()
        etag.update(self.item_serialize(item).encode())
        return '"%s"' % etag.hexdigest()

    def serialize(self, item: Item | Collection) -> str:
        if isinstance(item, Item):
            return self.item_serialize(item)
        return "\n".join(
            [self.item_serialize(item) for item in self.collection_items(item)]
        )

    def item_get_from_path(self, path: str) -> Optional[Item]:
        collection_slug, item_href = self.split_path(path)
        if collection_slug is None or item_href is None:
            return None

        collection = self.collection_get(collection_slug)
        if collection is None:
            return None

        return self.item_get(item_href, collection)

    def split_path(
        self,
        path: str,
    ) -> tuple[str, Optional[str]]:
        path = path.strip("/")
        path_parts = path.split("/", maxsplit=1)

        if len(path_parts) == 2:
            collection_path = path_parts[0]
            item_href = path_parts[1]
        else:
            collection_path = path_parts[0]
            item_href = None

        return collection_path, item_href


def format_datetime(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(dt.timestamp()))
