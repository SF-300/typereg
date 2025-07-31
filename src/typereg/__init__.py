"""
TypeReg - A powerful Python library for creating type registries with Pydantic integration.
"""

__version__ = "0.1.0"

# NOTE: Registry - base class with bound tag_kwargs
#       Registry root - direct subclass of Registry base class
# NOTE: NOT THREAD SAFE!!!

from typereg.dataclasses import tagged_dataclass
from typereg.registry import Registry, create_registry
from typereg.utils import (
    by_tag,
    get_tag_kwarg,
    get_tag_to_class_mapping,
    is_variant,
    tag_of,
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
