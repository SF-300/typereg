import dataclasses

import pytest
from pydantic import BaseModel

from typereg import (
    Registry,
    by_tag,
    create_registry,
    get_tag_to_class_mapping,
    is_variant,
    tag_of,
    tagged_dataclass,
    tags,
)


def test_basic_registry_creation():
    """Registry can be created with default parameters."""

    class TestRegistry(Registry):
        pass

    assert TestRegistry.__name__ == "TestRegistry"
    assert issubclass(TestRegistry, object)


def test_custom_tag_kwarg():
    """Registry can use custom tag keyword."""

    class TestRegistryKind(create_registry("kind")):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistryKind, kind="test"):  # type: ignore[misc]
        pass

    assert tags(TestRegistryKind) == {"test"}
    assert by_tag(TestRegistryKind, "test") is Variant


def test_concrete_variant_registration():
    """Concrete variants must provide a tag and get registered."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    assert tags(TestRegistry) == {"a", "b"}
    assert by_tag(TestRegistry, "a") is VariantA
    assert by_tag(TestRegistry, "b") is VariantB


def test_empty_tag_raises_error():
    """Empty tag should raise TypeError."""

    class TestRegistry(Registry):
        pass

    with pytest.raises(TypeError, match="tag must be a non-empty string"):

        @dataclasses.dataclass
        class EmptyTagVariant(TestRegistry, _type_tag=""):  # type: ignore[misc]
            pass


def test_non_string_tag_raises_error():
    """Non-string tag should raise TypeError."""

    class TestRegistry(Registry):
        pass

    with pytest.raises(TypeError, match="tag must be a non-empty string"):

        @dataclasses.dataclass
        class NonStringTagVariant(TestRegistry, _type_tag=123):  # type: ignore[misc]
            pass


def test_duplicate_tag_raises_error():
    """Duplicate tags should raise TypeError."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="duplicate"):  # type: ignore[misc]
        pass

    with pytest.raises(KeyError):

        @dataclasses.dataclass
        class VariantB(TestRegistry, _type_tag="duplicate"):  # type: ignore[misc]
            pass


def test_get_tag_to_class_mapping():
    """get_tag_to_class_mapping returns copy of mapping."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    class AbstractBase(TestRegistry, Registry):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantC(AbstractBase, _type_tag="c"):  # type: ignore[misc]
        pass

    mapping = get_tag_to_class_mapping(TestRegistry)
    expected = {"a": VariantA, "b": VariantB, "c": VariantC}
    assert mapping == expected

    # Verify it's a copy (modifying shouldn't affect registry)
    mapping["new"] = str
    assert "new" not in get_tag_to_class_mapping(TestRegistry)


def test_pydantic_tagged_union_basic():
    """Test basic Pydantic tagged union functionality."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="variant_a"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="variant_b"):  # type: ignore[misc]
        name: str

    class Container(BaseModel):
        item: TestRegistry  # type: ignore[valid-type]

    # Test parsing variant A
    container_a = Container.model_validate({"item": {"_type_tag": "variant_a", "value": 42}})
    assert isinstance(container_a.item, VariantA)
    assert container_a.item.value == 42

    # Test parsing variant B
    container_b = Container.model_validate({"item": {"_type_tag": "variant_b", "name": "hello"}})
    assert isinstance(container_b.item, VariantB)
    assert container_b.item.name == "hello"


def test_tagged_dataclass_basic():
    """Test basic tagged_dataclass functionality."""

    class TestRegistry(Registry):
        pass

    @tagged_dataclass
    class SimpleVariant(TestRegistry, _type_tag="simple"):  # type: ignore[misc]
        value: int
        name: str

    # Test that the tag field is automatically added
    instance = SimpleVariant(value=42, name="test")
    assert instance.value == 42
    assert instance.name == "test"
    assert instance._type_tag == "simple"  # type: ignore

    # Test that it's a proper dataclass
    assert dataclasses.is_dataclass(SimpleVariant)

    # Test that registry functions work
    assert tags(TestRegistry) == {"simple"}
    assert by_tag(TestRegistry, "simple") is SimpleVariant
    assert tag_of(TestRegistry, instance) == "simple"
    assert is_variant(TestRegistry, instance) is True


def test_tagged_dataclass_with_custom_tag_kwarg():
    """Test tagged_dataclass with custom tag keyword."""

    class DocumentRegistry(create_registry("kind")):
        pass

    @tagged_dataclass
    class TextDocument(DocumentRegistry, kind="text"):  # type: ignore[misc]
        content: str
        language: str = "en"

    # Test that the custom tag field is automatically added
    instance = TextDocument(content="Hello world", language="fr")
    assert instance.content == "Hello world"
    assert instance.language == "fr"
    assert instance.kind == "text"  # type: ignore

    # Test that it's a proper dataclass
    assert dataclasses.is_dataclass(TextDocument)

    # Test that registry functions work
    assert tags(DocumentRegistry) == {"text"}
    assert by_tag(DocumentRegistry, "text") is TextDocument


def test_tagged_dataclass_pydantic_integration():
    """Test that tagged_dataclass works with Pydantic serialization."""
    import pydantic

    class TestRegistry(Registry):
        pass

    @tagged_dataclass
    class DataVariant(TestRegistry, _type_tag="data"):  # type: ignore[misc]
        value: int
        name: str
        active: bool = True

    # Test direct variant serialization includes tag
    instance = DataVariant(value=42, name="test", active=False)
    result = pydantic.TypeAdapter(DataVariant).dump_python(instance)

    assert result["_type_tag"] == "data"
    assert result["value"] == 42
    assert result["name"] == "test"
    assert result["active"] is False

    # Test registry serialization
    registry_result = pydantic.TypeAdapter(TestRegistry).dump_python(instance)
    assert registry_result["_type_tag"] == "data"
    assert registry_result["value"] == 42

    # Test JSON roundtrip
    json_data = pydantic.TypeAdapter(DataVariant).dump_json(instance)
    restored = pydantic.TypeAdapter(DataVariant).validate_json(json_data)

    assert isinstance(restored, DataVariant)
    assert restored.value == 42
    assert restored.name == "test"
    assert restored.active is False
    assert restored._type_tag == "data"  # type: ignore
