# davish

A "minimal" implementation of CalDAV and CardDAV to use in conjunction with your backend of choice.


## What it does

Using this library you can add a limited but useful subset of CalDAV and CardDav endpoints to your application.

With this endpoints and a DAV client (for example [DAVx⁵](https://www.davx5.com/)) you can synchronize contacts and events to your smartphone, or everything that uses the DAV protocol (see [Supported Clients](#supported-clients)).

The library takes care of interpreting the DAV requests and providing adequate responses but is missing (intentionally) a lot of features. 
The aim of this library is not to provide a standalone DAV server but to extend your application, which means that everything that can be implemented externally has been removed.


## What's missing

A good chunk of the code is derived/inspired from [Radicale](https://github.com/Kozea/Radicale/).

Radicale has:
 * RFC-compliant DAV implementation
 * authentication support
 * rights support
 * filesystem storage
 * web interface
 * internal server
 * vcf/ics parsing and serializing

This library **does not**.

Additionaly this DAV methods are not implemented:
 * MKCALENDR
 * MKCOL
 * MOVE
 * PROPPATCH

which means that is not possible to use this library to create/update/delete the collections or move items in different collections. In my opinion this operations can be done in the application layer.


## How to use
This library expose a `handle_dav_request` method that accepts a WSGI environment (for example Django's `request.META`) and an instance of `BaseStorage` (see [here](#storage)).

All the heavy lifting is left to your backend.
This method handle the request and returns a response.

An example in Django:

```python
import davish
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from your_project import Storage


@csrf_exempt
def dav_view(request: HttpRequest, url: str) -> HttpResponse:
    storage = Storage()
    storage.user = request.user.username

    status, headers, content = davish.handle_dav_request(
        request.META,
        storage=storage,
    )

    return HttpResponse(status=status, headers=headers, content=content)
```


### Storage

The library is storage agnostic which means that the `BaseStorage` class must be extended to implement all methods used for CRUD operations on the collections and items.

More documentation will be written on this, and an example Django project will be added to the repository.

```python
from davy import BaseStorage

class Storage(BaseStorage):
    def collection_list(self) -> list[Collection]:
        ...

    def collection_get(
        self,
        slug: str,
    ) -> Optional[Collection]:
        ...

    def collection_items(
        self,
        collection: Collection,
    ) -> list[Item]:
        ...

    def item_get(
        self,
        href: str,
        collection: Collection,
    ) -> Optional[Item]:
        ...

    def item_serialize(self, item: Item) -> str:
        ...

    def item_time_range(self, item: Item) -> tuple[int, int]:
        ...

    def item_upload(
        self,
        href: str,
        item: Optional[Item],
        collection: Collection,
        content: str,
    ) -> Optional[Item]:
        ...

    def item_delete(
        self,
        item: Item,
    ) -> None:
        ...
```