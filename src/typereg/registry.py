import typing as t

from pydantic_core import core_schema as cs

from .base import REGISTRY_STATE, SENTINEL, RegistryState
from .utils import (
    NarrowingMapping,
    create_union_serializer,
    create_variant_serializer,
    get_parent_registry_root,
)


def _create_pydantic_tagged_union_schema(
    tag_to_class: t.Mapping[str, type], tag_kwarg: str, handler
) -> t.Any:
    """Create Pydantic schema for tagged unions."""
    # Create choices dict for tagged union
    choices = {tag: handler(variant_class) for tag, variant_class in tag_to_class.items()}

    # Create a serializer that adds the tag
    union_serializer = create_union_serializer(tag_to_class, tag_kwarg)

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

    def get_registry_pydantic_core_schema(cls, source_type, handler):
        # Check if cls is a registry root (direct or inheriting from our Registry family)
        try:
            state = REGISTRY_STATE[cls]
        except KeyError:
            return handler(source_type)

        # This is a registry root - create tagged union schema
        tag_to_class = state["tag_to_class"]
        return _create_pydantic_tagged_union_schema(tag_to_class, tag_kwarg, handler)

    def get_variant_pydantic_core_schema(cls, source_type, handler):
        # Find the registry root for this variant in our family
        registry = get_parent_registry_root(cls)
        if registry is None:
            raise AssertionError("No registry root found in this family")

        state = REGISTRY_STATE[registry]

        # Try to get the default schema for this class
        default_schema = handler(source_type)

        # Get the tag for this specific variant class
        try:
            tag = state["class_to_tag"][cls]
        except KeyError:
            # This variant is not registered (probably abstract), use default handling
            return default_schema

        # Create a serializer that adds the tag field
        variant_serializer = create_variant_serializer(tag, tag_kwarg)

        # Return the default schema with our custom serialization
        return {
            **default_schema,
            "serialization": cs.wrap_serializer_function_ser_schema(
                variant_serializer,
                schema=default_schema,
                info_arg=False,
            ),
        }

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
            # Use our closure function that has direct access to this Registry family
            return get_registry_pydantic_core_schema(cls, source_type, handler)

        def __init_subclass__(cls, **kwargs):
            # Extract the tag value using this registry family's tag_kwarg
            tag = kwargs.pop(tag_kwarg, SENTINEL)

            # Call parent __init_subclass__
            super().__init_subclass__(**kwargs)

            # Find the registry root for this class
            parent_registry = get_parent_registry_root(cls)

            # Check if this is a direct Registry subclass (becomes a new registry root)
            if Registry in cls.__bases__:
                # This is a new registry root - initialize its state
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
                cls.__get_pydantic_core_schema__ = classmethod(get_registry_pydantic_core_schema)  # type: ignore
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
            cls.__get_pydantic_core_schema__ = classmethod(get_variant_pydantic_core_schema)  # type: ignore

    return Registry


# Create the default Registry class for backward compatibility
Registry = create_registry("_type_tag")
