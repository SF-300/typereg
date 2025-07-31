import typing as t
from weakref import WeakKeyDictionary

SENTINEL = object()


class RegistryState(t.TypedDict):
    tag_to_class: t.MutableMapping[str, type]
    class_to_tag: t.MutableMapping[type, str]
    tag_kwarg: str


REGISTRY_STATE: WeakKeyDictionary[type, RegistryState] = WeakKeyDictionary()
