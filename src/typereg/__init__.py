"""
TypeReg - A powerful Python library for creating type registries with Pydantic integration.
"""

__version__ = "0.1.0"

from typereg.typereg import (
    Registry,
    by_tag,
    create_registry,
    get_tag_kwarg,
    get_tag_to_class_mapping,
    is_variant,
    tag_of,
    tagged_dataclass,
    tags,
)

__all__ = [
    "Registry",
    "by_tag",
    "create_registry",
    "get_tag_kwarg",
    "get_tag_to_class_mapping",
    "is_variant",
    "tag_of",
    "tagged_dataclass",
    "tags",
]
