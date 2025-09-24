import typing as t

from pydantic_core import core_schema as cs

from .base import REGISTRY_STATE
from .utils import get_parent_registry_root


def _create_pydantic_tagged_union_schema(
    tag_to_class: t.Mapping[str, type], tag_kwarg: str, handler
) -> t.Any:
    """Create Pydantic schema for tagged unions."""
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


def _create_union_serializer(tag_to_class: t.Mapping[str, type], tag_kwarg: str):
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


def _create_variant_serializer(tag: str, tag_kwarg: str):
    """Create a serializer for individual variants."""

    def variant_serializer(value, serializer_func):
        serialized = serializer_func(value)
        if isinstance(serialized, dict):
            # Read tag from instance if available, otherwise use class tag
            serialized[tag_kwarg] = getattr(value, tag_kwarg, tag)
        return serialized

    return variant_serializer


def get_registry_pydantic_core_schema(cls: type, source_type, handler, tag_kwarg: str):
    # Check if cls is a registry root (direct or inheriting from our Registry family)
    try:
        state = REGISTRY_STATE[cls]
    except KeyError:
        return handler(source_type)

    # This is a registry root - create tagged union schema
    tag_to_class = state["tag_to_class"]
    return _create_pydantic_tagged_union_schema(tag_to_class, tag_kwarg, handler)


def get_variant_pydantic_core_schema(cls: type, source_type, handler, tag_kwarg: str):
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
