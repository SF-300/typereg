import functools

from .base import REGISTRY_STATE, SENTINEL, RegistryState
from .pydantic import get_registry_pydantic_core_schema, get_variant_pydantic_core_schema
from .utils import (
    NarrowingMapping,
    get_parent_registry_root,
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

    class Registry:
        """
        Base class for creating type registries.
        Each direct subclass becomes its own registry that tracks its tagged variant subclasses.

        Subclassing rules:
        - Direct Registry subclass: becomes a new registry root
        - Derived registry: class Y(ExistingRegistry, Registry) creates hierarchical registries
        - Concrete variant: class X(Root, tag_kwarg="...")  # tag is REQUIRED and UNIQUE
        """

        @classmethod
        def __get_pydantic_core_schema__(cls, source_type, handler):
            return get_registry_pydantic_core_schema(cls, source_type, handler, tag_kwarg)

        def __init_subclass__(cls, **kwargs):
            tag = kwargs.pop(tag_kwarg, SENTINEL)

            super().__init_subclass__(**kwargs)

            parent_registry = get_parent_registry_root(cls)

            # Check if this is a direct Registry subclass (becomes a new registry root)
            if Registry in cls.__bases__:
                parent_state = (
                    RegistryState(
                        tag_to_class={},
                        class_to_tag={},
                        tag_kwarg=tag_kwarg,
                    )
                    if parent_registry is None
                    else REGISTRY_STATE[parent_registry]
                )

                REGISTRY_STATE[cls] = RegistryState(
                    tag_to_class=NarrowingMapping(parent_state["tag_to_class"]),
                    class_to_tag=NarrowingMapping(parent_state["class_to_tag"]),
                    tag_kwarg=tag_kwarg,
                )

                # Registry roots should not have tags themselves
                if tag is not SENTINEL:
                    raise TypeError(f"Registry root {cls.__name__} should not have {tag_kwarg}=")

                # Add the Pydantic schema method only to registry roots
                if "__get_pydantic_core_schema__" in cls.__dict__:
                    raise TypeError(
                        f"Registry root {cls.__name__} should not have own __get_pydantic_core_schema__"
                    )
                cls.__get_pydantic_core_schema__ = classmethod(
                    functools.partial(get_registry_pydantic_core_schema, tag_kwarg=tag_kwarg)
                )  # type: ignore
                return

            if parent_registry is None:
                # This class doesn't inherit from any registry, ignore
                return

            # Check for incompatible registry families
            registry_state = REGISTRY_STATE[parent_registry]

            # Get state from the registry root
            tag_to_class = registry_state["tag_to_class"]
            class_to_tag = registry_state["class_to_tag"]

            # Concrete variant: tag required + unique
            if tag is SENTINEL:
                return

            if not isinstance(tag, str) or not tag:
                raise TypeError(f"{tag_kwarg} must be a non-empty string")

            # Register the class in its registry
            tag_to_class[tag] = cls
            class_to_tag[cls] = tag

            # Add Pydantic schema method to variant classes so they include their tag when serialized
            if "__get_pydantic_core_schema__" in cls.__dict__:
                raise TypeError(
                    f"Variant {cls.__name__} should not have own __get_pydantic_core_schema__"
                )
            cls.__get_pydantic_core_schema__ = classmethod(
                functools.partial(get_variant_pydantic_core_schema, tag_kwarg=tag_kwarg)
            )  # type: ignore

    return Registry


# Create the default Registry class for backward compatibility
Registry = create_registry("_type_tag")
