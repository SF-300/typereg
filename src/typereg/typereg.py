import dataclasses
import functools
import typing as t
from abc import ABCMeta
from weakref import WeakKeyDictionary

from pydantic_core import core_schema as cs

# NOTE: Registry - base class with bound tag_kwargs
#       Registry root - direct subclass of Registry base class
# NOTE: NOT THREAD SAFE!!!


_SENTINEL = object()


class _RegistryState(t.TypedDict):
    tag_to_class: t.MutableMapping[str, type]
    class_to_tag: t.MutableMapping[type, str]
    tag_kwarg: str


_REGISTRY_STATE: WeakKeyDictionary[type, _RegistryState] = WeakKeyDictionary()


class _NarrowingMapping(t.MutableMapping):
    def __init__(self, store: t.MutableMapping):
        self._store = store
        self._own = set()

    def __getitem__(self, key: str) -> type:
        if key not in self._own:
            raise KeyError("Key not found")
        return self._store[key]

    def __setitem__(self, key: str, value: type) -> None:
        # Allow overwriting with same value (idempotent)
        if key in self._store and self._store[key] is not value:
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


def _extract_class_from_obj_or_cls(obj_or_cls: t.Any) -> type:
    return obj_or_cls if isinstance(obj_or_cls, type) else type(obj_or_cls)


def _get_registry_root_iter(cls: type) -> t.Iterator[type]:
    if cls in _REGISTRY_STATE:
        yield cls
    for base in cls.__mro__:  # Skip self
        if base in _REGISTRY_STATE:
            yield base


def _get_parent_registry_root(cls: type) -> type | None:
    """
    For Registry Roots: Skip itself, return first parent Registry Root
    For Variants: Return first Registry Root found
    """
    registry_roots_iter = iter(_get_registry_root_iter(cls))

    if cls in _REGISTRY_STATE:
        # If cls is a registry root, skip itself
        next(registry_roots_iter)

    return next(registry_roots_iter, None)


def _create_union_serializer(tag_to_class: t.Mapping[str, type], tag_kwarg: str):
    def union_serializer(value, serializer_func):
        for tag, variant_class in tag_to_class.items():
            if isinstance(value, variant_class):
                serialized = serializer_func(value)
                if isinstance(serialized, dict):
                    serialized[tag_kwarg] = tag
                return serialized
        return serializer_func(value)

    return union_serializer


def _create_variant_serializer(tag: str, tag_kwarg: str):
    def variant_serializer(value, serializer_func):
        serialized = serializer_func(value)
        if isinstance(serialized, dict):
            serialized[tag_kwarg] = tag
        return serialized

    return variant_serializer


def get_tag_to_class_mapping(registry: t.Any) -> dict[str, type]:
    cls = _extract_class_from_obj_or_cls(registry)
    root = _get_parent_registry_root(cls)
    if root is None:
        raise TypeError("Does not belong to a known registry")
    state = _REGISTRY_STATE[root]
    return dict(state["tag_to_class"])


def tags(registry: t.Any) -> set[str]:
    return set(get_tag_to_class_mapping(registry).keys())


def by_tag(registry: t.Any, tag: str) -> type:
    return get_tag_to_class_mapping(registry)[tag]


def tag_of(registry: t.Any, entry: t.Any) -> str | None:
    registry = _extract_class_from_obj_or_cls(registry)
    entry = _extract_class_from_obj_or_cls(entry)
    root = _get_parent_registry_root(registry)
    if root is None:
        raise TypeError("Does not belong to a known registry")
    state = _REGISTRY_STATE[root]
    for variant_cls, tag_value in state["class_to_tag"].items():
        if variant_cls is entry:
            return tag_value
    return None


def is_variant(registry: t.Any, obj_or_cls: t.Any) -> bool:
    """Check if obj_or_cls is a variant of the registry, including derived registries."""

    cls = _extract_class_from_obj_or_cls(obj_or_cls)
    tag_to_class = get_tag_to_class_mapping(registry)  # This now includes derived registry variants
    return cls in tag_to_class.values()


def get_tag_kwarg(registry: t.Any) -> str | None:
    """Get the tag keyword used by this registry."""

    cls = _extract_class_from_obj_or_cls(registry)
    root = _get_parent_registry_root(cls)
    if root is None:
        return None
    state = _REGISTRY_STATE[root]
    return state["tag_kwarg"]


def _create_pydantic_tagged_union_schema(
    tag_to_class: t.Mapping[str, type], tag_kwarg: str, handler
) -> t.Any:
    # Create choices dict for tagged union
    choices = {tag: handler(variant_class) for tag, variant_class in tag_to_class.items()}

    # Create a serializer that adds the tag
    union_serializer = _create_union_serializer(tag_to_class, tag_kwarg)

    # Create JsonOrPython schema to handle JSON vs Python validation differently
    return cs.json_or_python_schema(
        # For JSON mode, only allow tagged dicts
        json_schema=cs.tagged_union_schema(
            discriminator=tag_kwarg,
            choices=choices,
        ),
        # For Python mode, allow both instances and tagged dicts
        python_schema=cs.union_schema(
            [
                # Accept instances directly
                cs.is_instance_schema(tuple(tag_to_class.values())),
                # Accept tagged dicts in Python mode too
                cs.tagged_union_schema(
                    discriminator=tag_kwarg,
                    choices=choices,
                ),
            ]
        ),
        serialization=cs.wrap_serializer_function_ser_schema(
            union_serializer,
            schema=cs.any_schema(),  # The serializer handles everything
            info_arg=False,
        ),
    )


def create_registry(tag_kwarg: str = "_type_tag"):
    """
    Create a new Registry family with a specific tag keyword.

    This factory function creates a completely independent Registry class family.
    Each registry family is isolated and uses its own tag keyword.
    Registry families with different tag_kwarg values are incompatible and will
    raise errors if you try to mix them.

    The returned Registry class uses ABCMeta as its metaclass, making all
    Registry subclasses abstract base classes by default. Direct Registry subclasses
    become registry roots, while inheriting from both an existing registry and Registry
    creates hierarchical derived registries.
    """

    def _get_registry_pydantic_core_schema(cls, source_type, handler):
        # Check if cls is a registry root (direct or inheriting from our Registry family)
        try:
            state = _REGISTRY_STATE[cls]
        except KeyError:
            return handler(source_type)

        # This is a registry root - create tagged union schema
        tag_to_class = state["tag_to_class"]
        return _create_pydantic_tagged_union_schema(tag_to_class, tag_kwarg, handler)

    def _get_variant_pydantic_core_schema_for(cls, source_type, handler):
        # Find the registry root for this variant in our family
        registry = _get_parent_registry_root(cls)
        if registry is None:
            raise AssertionError("No registry root found in this family")

        state = _REGISTRY_STATE[registry]

        # Try to get the default schema for this class
        default_schema = handler(source_type)

        # Get the tag for this specific variant class
        try:
            tag = state["class_to_tag"][cls]
        except KeyError:
            # This variant is not registered (probably abstract), use default handling
            return default_schema

        # Create a serializer that adds the tag field
        variant_serializer = _create_variant_serializer(tag, tag_kwarg)

        # Return the default schema with our custom serialization
        return {
            **default_schema,
            "serialization": cs.wrap_serializer_function_ser_schema(
                variant_serializer,
                schema=default_schema,
                info_arg=False,
            ),
        }

    class Registry(metaclass=ABCMeta):
        """
        Base class for creating type registries.
        Each direct subclass becomes its own registry that tracks its tagged variant subclasses.

        Since Registry uses ABCMeta as its metaclass, all Registry subclasses are automatically
        abstract base classes. This means:
        - Registry roots are abstract by default

        Subclassing rules:
        - Direct Registry subclass: becomes a new registry root (abstract by default due to ABCMeta)
        - Derived registry: class Y(ExistingRegistry, Registry) creates hierarchical registries
        - Concrete variant: class X(Root, tag_kwarg="...")  # tag is REQUIRED and UNIQUE
        """

        @classmethod
        def __get_pydantic_core_schema__(cls, source_type, handler):
            # Use our closure function that has direct access to this Registry family
            return _get_registry_pydantic_core_schema(cls, source_type, handler)

        def __init_subclass__(cls, **kwargs):
            # Extract the tag value using this registry family's tag_kwarg
            tag = kwargs.pop(tag_kwarg, _SENTINEL)

            # Call parent __init_subclass__
            super().__init_subclass__(**kwargs)

            # Find the registry root for this class
            parent_registry = _get_parent_registry_root(cls)

            # Check if this is a direct Registry subclass (becomes a new registry root)
            if Registry in cls.__bases__:
                # This is a new registry root - initialize its state
                parent_state = (
                    _RegistryState(
                        tag_to_class={},
                        class_to_tag={},
                        tag_kwarg=tag_kwarg,
                    )
                    if parent_registry is None
                    else _REGISTRY_STATE[parent_registry]
                )

                _REGISTRY_STATE[cls] = _RegistryState(
                    tag_to_class=_NarrowingMapping(parent_state["tag_to_class"]),
                    class_to_tag=_NarrowingMapping(parent_state["class_to_tag"]),
                    tag_kwarg=tag_kwarg,
                )

                # Registry roots should not have tags themselves
                if tag is not _SENTINEL:
                    raise TypeError(f"Registry root {cls.__name__} should not have {tag_kwarg}=")

                # Add the Pydantic schema method only to registry roots
                if hasattr(cls, "__get_pydantic_core_schema__"):
                    raise TypeError(
                        f"Registry root {cls.__name__} should not have __get_pydantic_core_schema__"
                    )
                cls.__get_pydantic_core_schema__ = classmethod(
                    _get_registry_pydantic_core_schema
                )  # type: ignore
                return

            if parent_registry is None:
                # This class doesn't inherit from any registry, ignore
                return

            # Check for incompatible registry families
            registry_state = _REGISTRY_STATE[parent_registry]

            # Get state from the registry root
            tag_to_class = registry_state["tag_to_class"]
            class_to_tag = registry_state["class_to_tag"]

            # Concrete variant: tag required + unique
            if tag is _SENTINEL:
                return

            if not isinstance(tag, str) or not tag:
                raise TypeError(f"{tag_kwarg} must be a non-empty string")

            # Register the class in its registry
            tag_to_class[tag] = cls
            class_to_tag[cls] = tag

            # Add Pydantic schema method to variant classes so they include their tag when serialized
            if hasattr(cls, "__get_pydantic_core_schema__"):
                raise TypeError(
                    f"Variant {cls.__name__} already has __get_pydantic_core_schema__"
                )
            cls.__get_pydantic_core_schema__ = classmethod(
                _get_variant_pydantic_core_schema_for
            )  # type: ignore

    return Registry


# Create the default Registry class for backward compatibility
Registry = create_registry("_type_tag")


def _get_existing_field_info(cls: type, field_name: str) -> tuple[t.Any, t.Any]:
    annotations = getattr(cls, "__annotations__", {})
    annotation = annotations.get(field_name)
    default = getattr(cls, field_name, _SENTINEL)
    return annotation, default


def _tagged_dataclass(cls: type | None = None, /, **dataclass_kwargs) -> t.Any:
    """
    Create a stdlib dataclass that automatically includes the registry tag field.

    This decorator creates a regular stdlib dataclass but automatically injects
    the tag field from the Registry the class inherits from. The class MUST
    inherit from a Registry, otherwise dataclass creation will fail.

    Args:
        cls: The class to decorate (when used without parentheses)
        **dataclass_kwargs: Additional keyword arguments to pass to @dataclass

    Returns:
        A dataclass with the registry tag field automatically added

    Raises:
        TypeError: If the class doesn't inherit from a Registry

    Usage:
    ```python
    class MyRegistry(Registry):
        pass

    @tagged_dataclass
    class MyVariant(MyRegistry, _type_tag="my_variant"):
        value: int
        name: str

    # The resulting class is equivalent to:
    @dataclass
    class MyVariant(MyRegistry, _type_tag="my_variant"):
        value: int
        name: str
        _type_tag: str = "my_variant"  # Automatically added

    # Usage:
    instance = MyVariant(value=42, name="test")
    assert instance._type_tag == "my_variant"
    ```

    With custom tag keyword:
    ```python
    CustomRegistry = create_registry("kind")

    class MyRegistry(CustomRegistry):
        pass

    @tagged_dataclass
    class MyVariant(MyRegistry, kind="my_variant"):
        data: str

    instance = MyVariant(data="hello")
    assert instance.kind == "my_variant"
    ```
    """

    @functools.wraps(dataclasses.dataclass)
    def decorator(target_cls: type) -> type:
        # Check if the class inherits from a Registry and find its state
        if target_cls not in _REGISTRY_STATE:
            registry_root = _get_parent_registry_root(target_cls)
            if registry_root is None:
                raise TypeError(
                    f"Class {target_cls.__name__} must inherit from a Registry to use @tagged_dataclass. "
                    f"Make sure your class inherits from a Registry class created with create_registry() "
                    f"or the default Registry."
                )

            registry_state = _REGISTRY_STATE[registry_root]

            # Get the tag kwarg and value for this class
            tag_kwarg = registry_state["tag_kwarg"]
            class_to_tag = registry_state["class_to_tag"]

            # The class should already be registered by Registry.__init_subclass__
            if target_cls not in class_to_tag:
                raise TypeError(
                    f"Class {target_cls.__name__} is not registered in the registry. "
                    f"Make sure you provide the {tag_kwarg}= parameter when defining the class."
                )

            tag_value = class_to_tag[target_cls]

            # Get existing field information
            existing_annotation, existing_default = _get_existing_field_info(target_cls, tag_kwarg)

            if existing_annotation is None and existing_default is _SENTINEL:
                # Ensure __annotations__ exists
                if not hasattr(target_cls, "__annotations__"):
                    target_cls.__annotations__ = {}

                # Add tag field annotation and default
                target_cls.__annotations__[tag_kwarg] = t.Literal[tag_value]
                setattr(
                    target_cls,
                    tag_kwarg,
                    dataclasses.field(init=False, default=tag_value),
                )
            else:
                expected_annotation, expected_default = str, tag_value
                if (
                    existing_annotation != expected_annotation
                    or existing_default != expected_default
                ):
                    raise TypeError(
                        f"Class {target_cls.__name__} already has field '{tag_kwarg}' "
                        f"but it doesn't match the expected tag field. "
                        f"Expected: annotation={expected_annotation}, default={expected_default!r}. "
                        f"Found: annotation={existing_annotation}, default={existing_default!r}."
                    )

        # Apply the dataclass decorator with the tag field included
        return dataclasses.dataclass(**dataclass_kwargs)(target_cls)

    # Handle both @tagged_dataclass and @tagged_dataclass() usage
    if cls is None:
        return decorator
    else:
        return decorator(cls)


if t.TYPE_CHECKING:
    tagged_dataclass = dataclasses.dataclass  # type: ignore
else:
    tagged_dataclass = _tagged_dataclass
