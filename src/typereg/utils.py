import typing as t

from .base import REGISTRY_STATE, SENTINEL


def extract_class_from_obj_or_cls(obj_or_cls: t.Any) -> type:
    return obj_or_cls if isinstance(obj_or_cls, type) else type(obj_or_cls)


def get_registry_root_iter(cls: type) -> t.Iterator[type]:
    if cls in REGISTRY_STATE:
        yield cls
    for base in cls.__mro__:  # Skip self
        if base in REGISTRY_STATE:
            yield base


def get_parent_registry_root(cls: type) -> type | None:
    """
    For Registry Roots: Skip itself, return first parent Registry Root
    For Variants: Return first Registry Root found
    """
    registry_roots_iter = iter(get_registry_root_iter(cls))

    if cls in REGISTRY_STATE:
        # If cls is a registry root, skip itself
        next(registry_roots_iter)

    return next(registry_roots_iter, None)


def create_union_serializer(tag_to_class: t.Mapping[str, type], tag_kwarg: str):
    """Create a serializer for tagged unions."""

    def union_serializer(value, serializer_func):
        for tag, variant_class in tag_to_class.items():
            if isinstance(value, variant_class):
                serialized = serializer_func(value)
                if isinstance(serialized, dict):
                    serialized[tag_kwarg] = tag
                return serialized
        return serializer_func(value)

    return union_serializer


def create_variant_serializer(tag: str, tag_kwarg: str):
    """Create a serializer for individual variants."""

    def variant_serializer(value, serializer_func):
        serialized = serializer_func(value)
        if isinstance(serialized, dict):
            serialized[tag_kwarg] = tag
        return serialized

    return variant_serializer


def get_tag_to_class_mapping(registry: t.Any) -> dict[str, type]:
    """Get mapping from tags to classes for a registry."""
    cls = extract_class_from_obj_or_cls(registry)
    root = get_parent_registry_root(cls)
    if root is None:
        raise TypeError("Does not belong to a known registry")
    state = REGISTRY_STATE[root]
    return dict(state["tag_to_class"])


def tags(registry: t.Any) -> set[str]:
    """Get all tags for a registry."""
    return set(get_tag_to_class_mapping(registry).keys())


def by_tag(registry: t.Any, tag: str) -> type:
    """Get class by tag for a registry."""
    return get_tag_to_class_mapping(registry)[tag]


def tag_of(registry: t.Any, entry: t.Any) -> str | None:
    """Get tag of an entry in a registry."""
    registry = extract_class_from_obj_or_cls(registry)
    entry = extract_class_from_obj_or_cls(entry)
    root = get_parent_registry_root(registry)
    if root is None:
        raise TypeError("Does not belong to a known registry")
    state = REGISTRY_STATE[root]
    for variant_cls, tag_value in state["class_to_tag"].items():
        if variant_cls is entry:
            return tag_value
    return None


def is_variant(registry: t.Any, obj_or_cls: t.Any) -> bool:
    """Check if obj_or_cls is a variant of the registry, including derived registries."""
    cls = extract_class_from_obj_or_cls(obj_or_cls)
    tag_to_class = get_tag_to_class_mapping(registry)  # This now includes derived registry variants
    return cls in tag_to_class.values()


def get_tag_kwarg(registry: t.Any) -> str | None:
    """Get the tag keyword used by this registry."""
    cls = extract_class_from_obj_or_cls(registry)
    root = get_parent_registry_root(cls)
    if root is None:
        return None
    state = REGISTRY_STATE[root]
    return state["tag_kwarg"]


def get_existing_field_info(cls: type, field_name: str) -> tuple[t.Any, t.Any]:
    """Get existing field annotation and default value."""
    annotations = getattr(cls, "__annotations__", {})
    annotation = annotations.get(field_name)
    default = getattr(cls, field_name, SENTINEL)
    return annotation, default


class NarrowingMapping(t.MutableMapping):
    """A mapping that tracks which keys were added by this instance."""

    def __init__(self, store: t.MutableMapping):
        self._store = store
        self._own = set()

    def __getitem__(self, key: str) -> type:
        if key not in self._own:
            raise KeyError("Key not found")
        return self._store[key]

    def __setitem__(self, key: str, value: type) -> None:
        if key in self._store:
            raise KeyError(f"Tag '{key}' conflicts with existing variant")

        self._own.add(key)
        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        self._own.remove(key)
        del self._store[key]

    def __iter__(self) -> t.Iterator[str]:
        return iter(self._own)

    def __contains__(self, key) -> bool:
        return key in self._own

    def __len__(self) -> int:
        return len(self._own)
