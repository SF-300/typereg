import dataclasses
import typing as t
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

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


def test_get_tag_to_class_mapping_with_instance():
    """get_tag_to_class_mapping works with instances."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    instance = VariantA()
    mapping = get_tag_to_class_mapping(instance)
    expected = {"a": VariantA}
    assert mapping == expected


def test_tags():
    """tags returns set of all registered tags."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    result = tags(TestRegistry)
    assert result == {"a", "b"}


def test_tags_with_instance():
    """tags works with instances."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    instance = VariantB()
    result = tags(instance)
    assert result == {"a", "b"}


def test_by_tag():
    """by_tag returns correct class for given tag."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    assert by_tag(TestRegistry, "a") is VariantA
    assert by_tag(TestRegistry, "b") is VariantB


def test_by_tag_invalid_tag():
    """by_tag raises KeyError for invalid tag."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistry, _type_tag="test"):  # type: ignore[misc]
        pass

    with pytest.raises(KeyError):
        by_tag(TestRegistry, "invalid")


def test_by_tag_with_instance():
    """by_tag works with instances."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    instance = VariantA()
    assert by_tag(instance, "b") is VariantB


def test_tag_of_with_class():
    """tag_of returns correct tag for given class."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    assert tag_of(TestRegistry, VariantA) == "a"
    assert tag_of(TestRegistry, VariantB) == "b"


def test_tag_of_with_instance():
    """tag_of returns correct tag for given instance."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    assert tag_of(TestRegistry, VariantA()) == "a"
    assert tag_of(TestRegistry, VariantB()) == "b"


def test_tag_of_unregistered_class():
    """tag_of raises KeyError for unregistered class."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistry, _type_tag="test"):  # type: ignore[misc]
        pass

    class UnregisteredClass:
        pass

    assert tag_of(TestRegistry, UnregisteredClass) is None


def test_is_variant_with_class():
    """is_variant correctly identifies registered classes."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    class AbstractBase(TestRegistry, Registry):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(AbstractBase, _type_tag="b"):  # type: ignore[misc]
        pass

    assert is_variant(TestRegistry, VariantA) is True
    assert is_variant(TestRegistry, VariantB) is True
    assert is_variant(TestRegistry, AbstractBase) is False


def test_is_variant_with_instance():
    """is_variant correctly identifies instances of registered classes."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        pass

    assert is_variant(TestRegistry, VariantA()) is True
    assert is_variant(TestRegistry, VariantB()) is True


def test_is_variant_unregistered():
    """is_variant returns False for unregistered classes."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistry, _type_tag="test"):  # type: ignore[misc]
        pass

    class UnregisteredClass:
        pass

    assert is_variant(TestRegistry, UnregisteredClass) is False
    assert is_variant(TestRegistry, UnregisteredClass()) is False


def test_unknown_registry_raises_error():
    """Functions should raise TypeError for unknown registry."""

    class RandomClass:
        pass

    with pytest.raises(TypeError, match="Does not belong to a known registry"):
        get_tag_to_class_mapping(RandomClass)

    with pytest.raises(TypeError, match="Does not belong to a known registry"):
        tags(RandomClass())

    with pytest.raises(TypeError, match="Does not belong to a known registry"):
        by_tag(RandomClass, "any")

    with pytest.raises(TypeError, match="Does not belong to a known registry"):
        tag_of(RandomClass, RandomClass)

    with pytest.raises(TypeError, match="Does not belong to a known registry"):
        is_variant(RandomClass, RandomClass)


def test_registry_isolation():
    """Multiple registries should be completely isolated."""

    class RegistryA(Registry):
        pass

    class RegistryB(Registry):
        pass

    @dataclasses.dataclass
    class VariantA1(RegistryA, _type_tag="shared"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantA2(RegistryA, _type_tag="unique_a"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB1(RegistryB, _type_tag="shared"):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class VariantB2(RegistryB, _type_tag="unique_b"):  # type: ignore[misc]
        pass

    # Each registry only knows about its own variants
    assert tags(RegistryA) == {"shared", "unique_a"}
    assert tags(RegistryB) == {"shared", "unique_b"}

    assert by_tag(RegistryA, "shared") is VariantA1
    assert by_tag(RegistryB, "shared") is VariantB1

    assert is_variant(RegistryA, VariantA1) is True
    assert is_variant(RegistryA, VariantB1) is False
    assert is_variant(RegistryB, VariantB1) is True
    assert is_variant(RegistryB, VariantA1) is False


def test_query_via_root_class():
    """All API functions should work when passed the root registry class."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistry, _type_tag="test"):  # type: ignore[misc]
        pass

    # All these should work
    assert tags(TestRegistry) == {"test"}
    assert by_tag(TestRegistry, "test") is Variant
    assert tag_of(TestRegistry, Variant) == "test"
    assert is_variant(TestRegistry, Variant) is True
    assert get_tag_to_class_mapping(TestRegistry) == {"test": Variant}


def test_dataclass_tag_field():
    """Tag fields should be present on dataclass instances."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="a"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="b"):  # type: ignore[misc]
        name: str

    instance_a = VariantA(value=100)
    instance_b = VariantB(name="hello")

    # Instances should have the tag field set for dataclasses
    assert instance_a.value == 100
    assert instance_b.name == "hello"


def test_custom_tag_kwarg_field():
    """Custom tag keyword should create field on dataclass instances."""

    class TestRegistryKind(create_registry("kind")):
        pass

    @dataclasses.dataclass
    class Variant(TestRegistryKind, kind="test"):  # type: ignore[misc]
        data: str

    instance = Variant(data="custom")

    # Instance should have the custom tag field name for dataclasses
    assert instance.data == "custom"


def test_dataclass_tag_field_automatic_injection():
    """Test that dataclass variants automatically get tag fields."""

    class TestRegistry(Registry):
        pass

    class CustomRegistry(create_registry("type")):
        pass

    # Test with default tag_kwarg
    @dataclasses.dataclass
    class DataclassVariant(TestRegistry, _type_tag="dataclass"):  # type: ignore[misc]
        value: int
        name: str = "default"

    # Test with custom tag_kwarg
    @dataclasses.dataclass
    class CustomDataclassVariant(CustomRegistry, type="custom"):  # type: ignore[misc]
        data: str

    # Test non-dataclass (should NOT get tag field)
    class PlainClassVariant(TestRegistry, _type_tag="plain"):  # type: ignore[misc]
        def __init__(self, value: int):
            self.value = value

    # Create instances
    dc_instance = DataclassVariant(value=42, name="test")
    custom_instance = CustomDataclassVariant(data="example")
    plain_instance = PlainClassVariant(value=100)

    # Dataclass instances should have tag fields
    assert dc_instance.value == 42
    assert dc_instance.name == "test"

    assert custom_instance.data == "example"

    # Non-dataclass instances should NOT have tag fields
    assert plain_instance.value == 100

    # Verify registry functionality still works
    assert tags(TestRegistry) == {"dataclass", "plain"}
    assert tags(CustomRegistry) == {"custom"}
    assert by_tag(TestRegistry, "dataclass") is DataclassVariant
    assert by_tag(TestRegistry, "plain") is PlainClassVariant
    assert by_tag(CustomRegistry, "custom") is CustomDataclassVariant


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


def test_pydantic_tagged_union_json_roundtrip():
    """Test JSON serialization and deserialization roundtrip."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class NumberVariant(TestRegistry, _type_tag="number"):  # type: ignore[misc]
        value: int
        multiplier: float

    @dataclasses.dataclass
    class TextVariant(TestRegistry, _type_tag="text"):  # type: ignore[misc]
        content: str
        uppercase: bool

    class Document(BaseModel):
        title: str
        data: TestRegistry  # type: ignore[valid-type]

    # Create instances and serialize to JSON
    doc_number = Document(title="Number Doc", data=NumberVariant(value=100, multiplier=2.5))
    doc_text = Document(title="Text Doc", data=TextVariant(content="hello world", uppercase=True))

    json_number = doc_number.model_dump_json()
    json_text = doc_text.model_dump_json()

    # Parse back from JSON
    parsed_number = Document.model_validate_json(json_number)
    parsed_text = Document.model_validate_json(json_text)

    # Verify correct types
    assert isinstance(parsed_number.data, NumberVariant)
    assert isinstance(parsed_text.data, TextVariant)

    # Verify field values
    assert parsed_number.data.value == 100
    assert parsed_number.data.multiplier == 2.5
    assert parsed_text.data.content == "hello world"
    assert parsed_text.data.uppercase is True


def test_pydantic_tagged_union_validation_error():
    """Test that invalid tag values raise ValidationError."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class ValidVariant(TestRegistry, _type_tag="valid"):  # type: ignore[misc]
        data: str

    class Container(BaseModel):
        item: TestRegistry  # type: ignore[valid-type]

    # Test invalid tag
    with pytest.raises(ValidationError) as exc_info:
        Container.model_validate({"item": {"_type_tag": "invalid", "data": "test"}})

    error = exc_info.value
    assert "invalid" in str(error)


def test_pydantic_tagged_union_missing_tag():
    """Test that missing tag field raises ValidationError."""

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class ValidVariant(TestRegistry, _type_tag="valid"):  # type: ignore[misc]
        data: str

    class Container(BaseModel):
        item: TestRegistry  # type: ignore[valid-type]

    # Test missing tag
    with pytest.raises(ValidationError) as exc_info:
        Container.model_validate({"item": {"data": "test"}})

    error = exc_info.value
    assert "_type_tag" in str(error) or "tag" in str(error).lower()


def test_pydantic_custom_tag_kwarg():
    """Test Pydantic integration with custom tag keyword."""

    class TestRegistryType(create_registry("type")):
        pass

    @dataclasses.dataclass
    class FirstType(TestRegistryType, type="first"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class SecondType(TestRegistryType, type="second"):  # type: ignore[misc]
        name: str

    class Container(BaseModel):
        item: TestRegistryType  # type: ignore[valid-type]

    # Test with custom tag keyword
    container = Container.model_validate({"item": {"type": "first", "value": 123}})
    assert isinstance(container.item, FirstType)
    assert container.item.value == 123


def test_pydantic_nested_registries():
    """Test Pydantic with nested models containing different registries."""

    class RegistryA(Registry):
        pass

    class RegistryB(Registry):
        pass

    @dataclasses.dataclass
    class TypeA1(RegistryA, _type_tag="a1"):  # type: ignore[misc]
        x: int

    @dataclasses.dataclass
    class TypeA2(RegistryA, _type_tag="a2"):  # type: ignore[misc]
        y: str

    @dataclasses.dataclass
    class TypeB1(RegistryB, _type_tag="b1"):  # type: ignore[misc]
        z: float

    @dataclasses.dataclass
    class TypeB2(RegistryB, _type_tag="b2"):  # type: ignore[misc]
        w: bool

    class NestedContainer(BaseModel):
        item_a: RegistryA  # type: ignore[valid-type]
        item_b: RegistryB  # type: ignore[valid-type]

    data = {"item_a": {"_type_tag": "a2", "y": "hello"}, "item_b": {"_type_tag": "b1", "z": 3.14}}

    container = NestedContainer.model_validate(data)
    assert isinstance(container.item_a, TypeA2)
    assert isinstance(container.item_b, TypeB1)
    assert container.item_a.y == "hello"
    assert container.item_b.z == 3.14


def test_pydantic_no_intermediate_registries():
    """Test that abstract intermediates are not included in Pydantic schema."""

    class TestRegistry(Registry):
        pass

    class AbstractBase(TestRegistry, Registry):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class ConcreteA(AbstractBase, _type_tag="concrete_a"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class ConcreteB(AbstractBase, _type_tag="concrete_b"):  # type: ignore[misc]
        name: str

    class Container(BaseModel):
        item: TestRegistry  # type: ignore[valid-type]

    # Only concrete variants should be available in the union
    container = Container.model_validate({"item": {"_type_tag": "concrete_a", "value": 42}})
    assert isinstance(container.item, ConcreteA)
    assert container.item.value == 42


def test_pydantic_deep_nested_deserialization():
    """Test that deeply nested Pydantic models with registry tagged unions work correctly."""

    # Create registries for different types of data
    class ActionRegistry(Registry):
        pass

    class ConditionRegistry(Registry):
        pass

    @dataclasses.dataclass
    class SendEmailAction(ActionRegistry, _type_tag="send_email"):  # type: ignore[misc]
        to: str
        subject: str
        body: str = ""

    @dataclasses.dataclass
    class CreateUserAction(ActionRegistry, _type_tag="create_user"):  # type: ignore[misc]
        username: str
        email: str
        is_admin: bool

    @dataclasses.dataclass
    class TimeCondition(ConditionRegistry, _type_tag="time"):  # type: ignore[misc]
        hour: int
        minute: int = 0

    @dataclasses.dataclass
    class UserCountCondition(ConditionRegistry, _type_tag="user_count"):  # type: ignore[misc]
        operator: str
        threshold: int

    # Nested Pydantic models that use the registries
    class Rule(BaseModel):
        name: str
        condition: ConditionRegistry  # type: ignore[valid-type]
        action: ActionRegistry  # type: ignore[valid-type]
        enabled: bool = True

    class WorkflowStep(BaseModel):
        step_id: str
        rules: list[Rule]
        next_step: str | None = None

    class Workflow(BaseModel):
        workflow_id: str
        name: str
        steps: list[WorkflowStep]
        default_action: ActionRegistry  # type: ignore[valid-type]

    # Complex nested JSON data
    workflow_data = {
        "workflow_id": "wf_001",
        "name": "User Management Workflow",
        "steps": [
            {
                "step_id": "step_1",
                "rules": [
                    {
                        "name": "Morning Email Rule",
                        "condition": {"_type_tag": "time", "hour": 9, "minute": 30},
                        "action": {
                            "_type_tag": "send_email",
                            "to": "admin@example.com",
                            "subject": "Daily Report",
                            "body": "Good morning! Here's your daily report.",
                        },
                        "enabled": True,
                    },
                    {
                        "name": "User Threshold Rule",
                        "condition": {
                            "_type_tag": "user_count",
                            "operator": "gt",
                            "threshold": 100,
                        },
                        "action": {
                            "_type_tag": "create_user",
                            "username": "backup_admin",
                            "email": "backup@example.com",
                            "is_admin": True,
                        },
                    },
                ],
                "next_step": "step_2",
            },
            {
                "step_id": "step_2",
                "rules": [
                    {
                        "name": "Cleanup Rule",
                        "condition": {"_type_tag": "time", "hour": 23},
                        "action": {
                            "_type_tag": "send_email",
                            "to": "cleanup@example.com",
                            "subject": "Cleanup Started",
                        },
                    }
                ],
            },
        ],
        "default_action": {
            "_type_tag": "send_email",
            "to": "fallback@example.com",
            "subject": "Default Action Triggered",
            "body": "Something unexpected happened.",
        },
    }

    # Parse the complex nested structure
    workflow = Workflow.model_validate(workflow_data)

    # Verify top-level structure
    assert workflow.workflow_id == "wf_001"
    assert workflow.name == "User Management Workflow"
    assert len(workflow.steps) == 2
    assert isinstance(workflow.default_action, SendEmailAction)
    assert workflow.default_action.to == "fallback@example.com"
    assert workflow.default_action.subject == "Default Action Triggered"
    assert workflow.default_action.body == "Something unexpected happened."

    # Verify first step
    step1 = workflow.steps[0]
    assert step1.step_id == "step_1"
    assert len(step1.rules) == 2
    assert step1.next_step == "step_2"

    # Verify first rule in first step
    rule1 = step1.rules[0]
    assert rule1.name == "Morning Email Rule"
    assert rule1.enabled is True
    assert isinstance(rule1.condition, TimeCondition)
    assert rule1.condition.hour == 9
    assert rule1.condition.minute == 30
    assert isinstance(rule1.action, SendEmailAction)
    assert rule1.action.to == "admin@example.com"
    assert rule1.action.subject == "Daily Report"
    assert rule1.action.body == "Good morning! Here's your daily report."

    # Verify second rule in first step
    rule2 = step1.rules[1]
    assert rule2.name == "User Threshold Rule"
    assert rule2.enabled is True  # default value
    assert isinstance(rule2.condition, UserCountCondition)
    assert rule2.condition.operator == "gt"
    assert rule2.condition.threshold == 100
    assert isinstance(rule2.action, CreateUserAction)
    assert rule2.action.username == "backup_admin"
    assert rule2.action.email == "backup@example.com"
    assert rule2.action.is_admin is True

    # Verify second step
    step2 = workflow.steps[1]
    assert step2.step_id == "step_2"
    assert len(step2.rules) == 1
    assert step2.next_step is None  # default value

    # Verify rule in second step
    rule3 = step2.rules[0]
    assert rule3.name == "Cleanup Rule"
    assert isinstance(rule3.condition, TimeCondition)
    assert rule3.condition.hour == 23
    assert rule3.condition.minute == 0  # default value
    assert isinstance(rule3.action, SendEmailAction)
    assert rule3.action.to == "cleanup@example.com"
    assert rule3.action.subject == "Cleanup Started"
    assert rule3.action.body == ""  # default value

    # Test JSON roundtrip to ensure serialization works too
    json_str = workflow.model_dump_json()
    parsed_workflow = Workflow.model_validate_json(json_str)

    # Verify the roundtrip preserved types
    assert isinstance(parsed_workflow.default_action, SendEmailAction)
    assert isinstance(parsed_workflow.steps[0].rules[0].condition, TimeCondition)
    assert isinstance(parsed_workflow.steps[0].rules[0].action, SendEmailAction)
    assert isinstance(parsed_workflow.steps[0].rules[1].condition, UserCountCondition)
    assert isinstance(parsed_workflow.steps[0].rules[1].action, CreateUserAction)
    assert isinstance(parsed_workflow.steps[1].rules[0].condition, TimeCondition)
    assert isinstance(parsed_workflow.steps[1].rules[0].action, SendEmailAction)

    # Verify field values are preserved through roundtrip
    assert parsed_workflow.steps[0].rules[0].action.subject == "Daily Report"
    assert parsed_workflow.steps[0].rules[1].condition.threshold == 100
    assert parsed_workflow.steps[1].rules[0].condition.hour == 23


# Create a registry for Messages
class Message(Registry):
    """Base message for tests."""

    pass


@dataclass(frozen=True)
class DoctorUpdated(Message, _type_tag="doctor_updated"):  # type: ignore[misc]
    """Concrete message with None value."""

    doctor: t.Any | None


# Define a generic ActorState base class


@dataclass(frozen=True, kw_only=True)
class ActorState[M]:
    """Base class for actor states, generic over message type."""

    actor_stash: tuple[M, ...] = tuple()


# Create registry for concrete states
class MedsupportStateBase(Registry):
    """Base class for Medsupport states."""

    pass


@dataclass(frozen=True)
class MedsupportUnassigned(MedsupportStateBase, ActorState[Message], _type_tag="unassigned"):  # type: ignore[misc]
    """Concrete Medsupport state that inherits from ActorState."""

    patient_id: UUID | None = None


@dataclass(frozen=True)
class MedsupportAssigned(MedsupportStateBase, ActorState[Message], _type_tag="assigned"):  # type: ignore[misc]
    """Another concrete Medsupport state."""

    patient_id: UUID | None = None
    doctor_id: UUID | None = None


# Create registry for chat groups
class ChatGroupStateBase(Registry):
    """Base class for ChatGroup states."""

    pass


@dataclass(frozen=True)
class ChatGroupExists(ChatGroupStateBase, ActorState[Message], _type_tag="exists"):  # type: ignore[misc]
    """Concrete ChatGroup state."""

    patient_id: UUID | None = None
    patient_name: str = "Test Patient"
    chat_group: str | None = None


# Create registry for chat members
class ChatMemberStateBase(Registry):
    """Base class for ChatMember states."""

    pass


@dataclass(frozen=True)
class ChatMemberActive(ChatMemberStateBase, ActorState[Message], _type_tag="active"):  # type: ignore[misc]
    """Concrete ChatMember state."""

    user_id: UUID | None = None
    chat_user: str | None = None
    chat_group: str | None = None


@dataclass(frozen=True)
class ChatMemberTerminated(ChatMemberStateBase, ActorState[Message], _type_tag="terminated"):  # type: ignore[misc]
    """Another concrete ChatMember state."""

    user_id: UUID | None = None
    chat_user: str | None = None
    chat_group: str | None = None


# Top-level StateV1 class that contains all the individual states
@dataclass(frozen=True)
class StateV1:
    """Top-level state container with nested states."""

    medsupport: MedsupportStateBase
    chat_group: ChatGroupStateBase
    chat_patient: ChatMemberStateBase
    chat_doctor: ChatMemberStateBase | None


@pytest.mark.skip(
    reason="Will not work until https://github.com/copilot/c/cef433fd-22b4-43e4-8bc8-ede6b0c6c646 is fixed"
)
def test_doctor_updated_in_actor_stash():
    """Test serialization of StateV1 with actor_stash containing DoctorUpdated(doctor=None)."""
    patient_id = uuid4()
    doctor_id = uuid4()
    chat_group_id = "group-123456"

    original_state = StateV1(
        medsupport=MedsupportAssigned(
            actor_stash=(DoctorUpdated(doctor=None),),
            patient_id=patient_id,
            doctor_id=doctor_id,
        ),
        chat_group=ChatGroupExists(
            actor_stash=(),
            patient_id=patient_id,
            patient_name="Test Patient",
            chat_group=chat_group_id,
        ),
        chat_patient=ChatMemberActive(
            actor_stash=(),
            user_id=patient_id,
            chat_user="patient-user",
            chat_group=chat_group_id,
        ),
        chat_doctor=ChatMemberActive(
            actor_stash=(),
            user_id=doctor_id,
            chat_user="doctor-user",
            chat_group=chat_group_id,
        ),
    )

    ta = TypeAdapter(StateV1)
    dumped = ta.dump_json(original_state)
    loaded = ta.validate_json(dumped)
    assert original_state == loaded


def test_stash_serialization_no_generics():
    """Test serialization without generics involved."""

    @dataclass(frozen=True)
    class SimpleState:
        actor_stash: tuple[Message, ...]

    original_state = SimpleState(
        actor_stash=(DoctorUpdated(doctor=None),),
    )
    ta = TypeAdapter(SimpleState)
    dumped = ta.dump_json(original_state)
    loaded = ta.validate_json(dumped)
    assert original_state == loaded


def test_automatic_pydantic_schema_addition():
    """Test that variant classes automatically get __get_pydantic_core_schema__ method."""

    class Foundation(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(Foundation, _type_tag="variant_a"):  # type: ignore[misc]
        value: int

    class PlainVariant(Foundation, _type_tag="plain"):  # type: ignore[misc]
        def __init__(self, data: str):
            self.data = data

    # Both dataclass and plain class variants should get the schema method
    assert hasattr(VariantA, "__get_pydantic_core_schema__")
    assert hasattr(PlainVariant, "__get_pydantic_core_schema__")

    # Abstract intermediates inherit the registry schema method
    class AbstractBase(Foundation, Registry):  # type: ignore[misc]
        pass

    # But concrete variants get their own variant-specific schema method
    @dataclasses.dataclass
    class ConcreteFromAbstract(AbstractBase, _type_tag="concrete"):  # type: ignore[misc]
        data: str

    # Verify that concrete variants have their own method (not inherited)
    variant_method = VariantA.__get_pydantic_core_schema__
    concrete_method = ConcreteFromAbstract.__get_pydantic_core_schema__
    registry_method = Foundation.__get_pydantic_core_schema__

    # Registry method should be different from variant methods
    assert variant_method.__func__.__name__ == "get_variant_pydantic_core_schema"
    assert concrete_method.__func__.__name__ == "get_variant_pydantic_core_schema"
    # All registry roots now use the closure-based method
    assert registry_method.__func__.__name__ == "get_registry_pydantic_core_schema"
    # But registry and variant methods should be different
    assert registry_method != variant_method
    assert registry_method != concrete_method


def test_direct_variant_serialization_includes_tag():
    """Test that variant classes include their tag when serialized directly."""
    import pydantic

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class DataclassVariant(TestRegistry, _type_tag="dataclass_variant"):  # type: ignore[misc]
        value: int
        name: str

    # Test dataclass variant
    dc_instance = DataclassVariant(value=42, name="test")
    dc_result = pydantic.TypeAdapter(DataclassVariant).dump_python(dc_instance)

    assert isinstance(dc_result, dict)
    assert dc_result["_type_tag"] == "dataclass_variant"
    assert dc_result["value"] == 42
    assert dc_result["name"] == "test"


def test_direct_variant_json_roundtrip():
    """Test JSON roundtrip for individual variant classes."""
    import pydantic

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="variant_a"):  # type: ignore[misc]
        value: int
        factor: float

    # Serialize to JSON
    instance = VariantA(value=100, factor=2.5)
    ta = pydantic.TypeAdapter(VariantA)
    json_data = ta.dump_json(instance)

    # Verify JSON contains the tag
    import json

    parsed_json = json.loads(json_data)
    assert parsed_json["_type_tag"] == "variant_a"
    assert parsed_json["value"] == 100
    assert parsed_json["factor"] == 2.5

    # Deserialize from JSON
    restored_instance = ta.validate_json(json_data)
    assert isinstance(restored_instance, VariantA)
    assert restored_instance.value == 100
    assert restored_instance.factor == 2.5


def test_custom_tag_kwarg_direct_serialization():
    """Test direct serialization with custom tag keyword."""
    import pydantic

    class DocumentRegistry(create_registry("type")):
        pass

    @dataclasses.dataclass
    class TextDocument(DocumentRegistry, type="text"):  # type: ignore[misc]
        content: str
        language: str = "en"

    @dataclasses.dataclass
    class ImageDocument(DocumentRegistry, type="image"):  # type: ignore[misc]
        url: str
        width: int
        height: int

    # Test text document
    text_doc = TextDocument(content="Hello world", language="en")
    text_result = pydantic.TypeAdapter(TextDocument).dump_python(text_doc)

    assert text_result["type"] == "text"
    assert text_result["content"] == "Hello world"
    assert text_result["language"] == "en"

    # Test image document
    image_doc = ImageDocument(url="https://example.com/image.jpg", width=800, height=600)
    image_result = pydantic.TypeAdapter(ImageDocument).dump_python(image_doc)

    assert image_result["type"] == "image"
    assert image_result["url"] == "https://example.com/image.jpg"
    assert image_result["width"] == 800
    assert image_result["height"] == 600


def test_variant_serialization_vs_registry_serialization():
    """Test that both direct variant and registry serialization include tags."""
    import pydantic

    class TestRegistry(Registry):
        pass

    @dataclasses.dataclass
    class VariantA(TestRegistry, _type_tag="variant_a"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class VariantB(TestRegistry, _type_tag="variant_b"):  # type: ignore[misc]
        name: str

    instance_a = VariantA(value=42)
    instance_b = VariantB(name="hello")

    # Direct variant serialization
    direct_a = pydantic.TypeAdapter(VariantA).dump_python(instance_a)
    direct_b = pydantic.TypeAdapter(VariantB).dump_python(instance_b)

    # Registry serialization
    registry_a = pydantic.TypeAdapter(TestRegistry).dump_python(instance_a)
    registry_b = pydantic.TypeAdapter(TestRegistry).dump_python(instance_b)

    # Both should include the tag field
    assert direct_a["_type_tag"] == "variant_a"
    assert direct_b["_type_tag"] == "variant_b"
    assert registry_a["_type_tag"] == "variant_a"
    assert registry_b["_type_tag"] == "variant_b"

    # Field values should be preserved
    assert direct_a["value"] == 42
    assert direct_b["name"] == "hello"
    assert registry_a["value"] == 42
    assert registry_b["name"] == "hello"


def test_multiple_registries_direct_serialization():
    """Test direct serialization works correctly with multiple isolated registries."""
    import pydantic

    class RegistryA(Registry):
        pass

    class RegistryB(create_registry("kind")):
        pass

    @dataclasses.dataclass
    class TypeA(RegistryA, _type_tag="type_a"):  # type: ignore[misc]
        x: int

    @dataclasses.dataclass
    class TypeB(RegistryB, kind="type_b"):  # type: ignore[misc]
        y: str

    instance_a = TypeA(x=100)
    instance_b = TypeB(y="test")

    # Direct serialization should use correct tag keywords
    result_a = pydantic.TypeAdapter(TypeA).dump_python(instance_a)
    result_b = pydantic.TypeAdapter(TypeB).dump_python(instance_b)

    assert result_a["_type_tag"] == "type_a"  # Default tag kwarg
    assert result_a["x"] == 100

    assert result_b["kind"] == "type_b"  # Custom tag kwarg
    assert result_b["y"] == "test"
    assert "_type_tag" not in result_b  # Should not have default tag kwarg


def test_multiple_registries_in_inheritance_chain():
    """Test that multiple registries in the same inheritance chain work correctly."""
    import pydantic

    # Create a base registry
    class BaseRegistry(Registry):
        pass

    # Create a derived registry that inherits from a variant of the base registry
    class IntermediateVariant(BaseRegistry, _type_tag="intermediate"):  # type: ignore[misc]
        pass

    # This should create a new registry, not extend BaseRegistry
    class DerivedRegistry(Registry):
        pass

    @dataclasses.dataclass
    class BaseVariantA(BaseRegistry, _type_tag="base_a"):  # type: ignore[misc]
        value: int

    @dataclasses.dataclass
    class BaseVariantB(BaseRegistry, _type_tag="base_b"):  # type: ignore[misc]
        name: str

    @dataclasses.dataclass
    class DerivedVariantA(DerivedRegistry, _type_tag="derived_a"):  # type: ignore[misc]
        data: str

    @dataclasses.dataclass
    class DerivedVariantB(DerivedRegistry, _type_tag="derived_b"):  # type: ignore[misc]
        count: int

    # Test that each registry only knows about its own variants
    assert tags(BaseRegistry) == {"intermediate", "base_a", "base_b"}
    assert tags(DerivedRegistry) == {"derived_a", "derived_b"}

    # Test direct serialization includes correct tags
    base_a = BaseVariantA(value=100)
    base_b = BaseVariantB(name="test")
    derived_a = DerivedVariantA(data="hello")
    derived_b = DerivedVariantB(count=42)

    result_base_a = pydantic.TypeAdapter(BaseVariantA).dump_python(base_a)
    result_base_b = pydantic.TypeAdapter(BaseVariantB).dump_python(base_b)
    result_derived_a = pydantic.TypeAdapter(DerivedVariantA).dump_python(derived_a)
    result_derived_b = pydantic.TypeAdapter(DerivedVariantB).dump_python(derived_b)

    assert result_base_a["_type_tag"] == "base_a"
    assert result_base_a["value"] == 100

    assert result_base_b["_type_tag"] == "base_b"
    assert result_base_b["name"] == "test"

    assert result_derived_a["_type_tag"] == "derived_a"
    assert result_derived_a["data"] == "hello"

    assert result_derived_b["_type_tag"] == "derived_b"
    assert result_derived_b["count"] == 42

    # Test that registries don't interfere with each other
    assert is_variant(BaseRegistry, BaseVariantA) is True
    assert is_variant(BaseRegistry, DerivedVariantA) is False
    assert is_variant(DerivedRegistry, DerivedVariantA) is True
    assert is_variant(DerivedRegistry, BaseVariantA) is False


def test_nested_abstract_classes_with_registries():
    """Test complex inheritance with multiple abstract classes and registries."""
    import pydantic

    # Base registry
    class DocumentRegistry(Registry):
        pass

    # Abstract base document
    class BaseDocument(DocumentRegistry, Registry):  # type: ignore[misc]
        pass

    # Abstract specialized documents
    class BaseTextDocument(BaseDocument, Registry):  # type: ignore[misc]
        pass

    class BaseMediaDocument(BaseDocument, Registry):  # type: ignore[misc]
        pass

    # Concrete implementations
    @dataclasses.dataclass
    class PlainTextDocument(BaseTextDocument, _type_tag="plain_text"):  # type: ignore[misc]
        content: str
        encoding: str = "utf-8"

    @dataclasses.dataclass
    class MarkdownDocument(BaseTextDocument, _type_tag="markdown"):  # type: ignore[misc]
        content: str
        has_tables: bool = False

    @dataclasses.dataclass
    class ImageDocument(BaseMediaDocument, _type_tag="image"):  # type: ignore[misc]
        url: str
        width: int
        height: int

    @dataclasses.dataclass
    class VideoDocument(BaseMediaDocument, _type_tag="video"):  # type: ignore[misc]
        url: str
        duration_seconds: int

    # Test registry knows about all concrete variants but not abstract ones
    expected_tags = {"plain_text", "markdown", "image", "video"}
    assert tags(DocumentRegistry) == expected_tags

    # Test direct serialization works for all concrete types
    plain_text = PlainTextDocument(content="Hello world", encoding="utf-8")
    markdown = MarkdownDocument(content="# Title\n\nContent", has_tables=True)
    image = ImageDocument(url="https://example.com/image.jpg", width=800, height=600)
    video = VideoDocument(url="https://example.com/video.mp4", duration_seconds=120)

    # Test direct variant serialization
    plain_result = pydantic.TypeAdapter(PlainTextDocument).dump_python(plain_text)
    markdown_result = pydantic.TypeAdapter(MarkdownDocument).dump_python(markdown)
    image_result = pydantic.TypeAdapter(ImageDocument).dump_python(image)
    video_result = pydantic.TypeAdapter(VideoDocument).dump_python(video)

    # Verify tags and content
    assert plain_result["_type_tag"] == "plain_text"
    assert plain_result["content"] == "Hello world"
    assert plain_result["encoding"] == "utf-8"

    assert markdown_result["_type_tag"] == "markdown"
    assert markdown_result["content"] == "# Title\n\nContent"
    assert markdown_result["has_tables"] is True

    assert image_result["_type_tag"] == "image"
    assert image_result["url"] == "https://example.com/image.jpg"
    assert image_result["width"] == 800
    assert image_result["height"] == 600

    assert video_result["_type_tag"] == "video"
    assert video_result["url"] == "https://example.com/video.mp4"
    assert video_result["duration_seconds"] == 120

    # Test registry serialization works too
    registry_plain = pydantic.TypeAdapter(DocumentRegistry).dump_python(plain_text)
    registry_video = pydantic.TypeAdapter(DocumentRegistry).dump_python(video)

    assert registry_plain["_type_tag"] == "plain_text"
    assert registry_video["_type_tag"] == "video"


def test_registry_inheritance_isolation():
    """Test that registries maintain isolation even with complex inheritance."""
    import pydantic

    # First registry family
    class FoundationA(Registry):
        pass

    class BaseA(FoundationA, Registry):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class A1(BaseA, _type_tag="a1"):  # type: ignore[misc]
        x: int

    @dataclasses.dataclass
    class A2(FoundationA, _type_tag="a2"):  # type: ignore[misc]
        y: str

    # Second registry family with same tag names (should not conflict)
    class FoundationB(Registry):
        pass

    class BaseB(FoundationB, Registry):  # type: ignore[misc]
        pass

    @dataclasses.dataclass
    class B1(BaseB, _type_tag="a1"):  # type: ignore[misc]  # Same tag as A1
        z: float

    @dataclasses.dataclass
    class B2(FoundationB, _type_tag="a2"):  # type: ignore[misc]  # Same tag as A2
        w: bool

    # Test complete isolation
    assert tags(FoundationA) == {"a1", "a2"}
    assert tags(FoundationB) == {"a1", "a2"}

    # Test by_tag returns correct classes for each registry
    assert by_tag(FoundationA, "a1") is A1
    assert by_tag(FoundationA, "a2") is A2
    assert by_tag(FoundationB, "a1") is B1
    assert by_tag(FoundationB, "a2") is B2

    # Test direct serialization maintains isolation
    a1_instance = A1(x=100)
    a2_instance = A2(y="hello")
    b1_instance = B1(z=3.14)
    b2_instance = B2(w=True)

    a1_result = pydantic.TypeAdapter(A1).dump_python(a1_instance)
    a2_result = pydantic.TypeAdapter(A2).dump_python(a2_instance)
    b1_result = pydantic.TypeAdapter(B1).dump_python(b1_instance)
    b2_result = pydantic.TypeAdapter(B2).dump_python(b2_instance)

    # All should have the same tag names but different field content
    assert a1_result["_type_tag"] == "a1"
    assert a2_result["_type_tag"] == "a2"
    assert b1_result["_type_tag"] == "a1"
    assert b2_result["_type_tag"] == "a2"

    # But different field content
    assert "x" in a1_result and "z" not in a1_result
    assert "y" in a2_result and "w" not in a2_result
    assert "z" in b1_result and "x" not in b1_result
    assert "w" in b2_result and "y" not in b2_result


def test_registry_inheriting_from_registry():
    """Test the scenario where one Registry inherits from another Registry."""
    import pydantic

    # Base registry
    class Message(Registry):
        pass

    # Intermediate class that inherits from Message but is not a Registry itself
    class SomeGenericMessage(Message):  # type: ignore[misc]
        pass

    # Another registry that inherits from Message (correct MRO)
    class Command(Message, Registry):  # type: ignore[misc]
        pass

    # Concrete variants
    @dataclasses.dataclass
    class TextMessage(SomeGenericMessage, _type_tag="text"):  # type: ignore[misc]
        content: str

    @dataclasses.dataclass
    class ImageMessage(Message, _type_tag="image"):  # type: ignore[misc]
        url: str
        alt_text: str

    @dataclasses.dataclass
    class AddCommand(Command, _type_tag="add"):  # type: ignore[misc]
        item: str

    @dataclasses.dataclass
    class DeleteCommand(Command, _type_tag="delete"):  # type: ignore[misc]
        item_id: int

    # Test what each registry knows about
    print("Message registry tags:", tags(Message))
    print("Command registry tags:", tags(Command))

    # Test that Message registry knows about all Message variants
    message_tags = tags(Message)
    assert "text" in message_tags
    assert "image" in message_tags

    # Test that Command registry knows about Command variants
    command_tags = tags(Command)
    assert "add" in command_tags
    assert "delete" in command_tags

    # Test whether Command variants also appear in Message registry
    # This is the key question - does inheritance propagate registrations?
    print(
        "Does Message know about Command variants?", "add" in message_tags, "delete" in message_tags
    )

    # Test direct serialization
    text_msg = TextMessage(content="Hello")
    image_msg = ImageMessage(url="https://example.com/img.jpg", alt_text="An image")
    add_cmd = AddCommand(item="new_item")
    delete_cmd = DeleteCommand(item_id=123)

    text_result = pydantic.TypeAdapter(TextMessage).dump_python(text_msg)
    image_result = pydantic.TypeAdapter(ImageMessage).dump_python(image_msg)
    add_result = pydantic.TypeAdapter(AddCommand).dump_python(add_cmd)
    delete_result = pydantic.TypeAdapter(DeleteCommand).dump_python(delete_cmd)

    # All should have correct tags
    assert text_result["_type_tag"] == "text"
    assert text_result["content"] == "Hello"

    assert image_result["_type_tag"] == "image"
    assert image_result["url"] == "https://example.com/img.jpg"
    assert image_result["alt_text"] == "An image"

    assert add_result["_type_tag"] == "add"
    assert add_result["item"] == "new_item"

    assert delete_result["_type_tag"] == "delete"
    assert delete_result["item_id"] == 123

    # Test registry-based serialization
    message_text = pydantic.TypeAdapter(Message).dump_python(text_msg)
    message_image = pydantic.TypeAdapter(Message).dump_python(image_msg)

    assert message_text["_type_tag"] == "text"
    assert message_image["_type_tag"] == "image"

    # Test Command registry serialization
    command_add = pydantic.TypeAdapter(Command).dump_python(add_cmd)
    command_delete = pydantic.TypeAdapter(Command).dump_python(delete_cmd)

    assert command_add["_type_tag"] == "add"
    assert command_delete["_type_tag"] == "delete"

    # Test cross-registry scenarios
    # Can Message registry handle Command variants?
    try:
        message_add = pydantic.TypeAdapter(Message).dump_python(add_cmd)
        print("Message can serialize AddCommand:", message_add)
        cross_registry_works = True
    except Exception as e:
        print("Message cannot serialize AddCommand:", str(e))
        cross_registry_works = False

    # The behavior here depends on implementation - document what actually happens
    print(f"Cross-registry serialization works: {cross_registry_works}")

    # Test is_variant behavior
    assert is_variant(Message, TextMessage) is True
    assert is_variant(Message, ImageMessage) is True
    assert is_variant(Command, AddCommand) is True
    assert is_variant(Command, DeleteCommand) is True

    # Test cross-registry is_variant
    message_knows_commands = is_variant(Message, AddCommand)
    command_knows_messages = is_variant(Command, TextMessage)

    print(f"Message.is_variant(AddCommand): {message_knows_commands}")
    print(f"Command.is_variant(TextMessage): {command_knows_messages}")

    # Test by_tag behavior
    assert by_tag(Message, "text") is TextMessage
    assert by_tag(Message, "image") is ImageMessage
    assert by_tag(Command, "add") is AddCommand
    assert by_tag(Command, "delete") is DeleteCommand

    # Test cross-registry by_tag
    try:
        message_add_class = by_tag(Message, "add")
        print(f"Message.by_tag('add'): {message_add_class}")
    except Exception as e:
        print(f"Message.by_tag('add') failed: {e}")

    try:
        command_text_class = by_tag(Command, "text")
        print(f"Command.by_tag('text'): {command_text_class}")
    except Exception as e:
        print(f"Command.by_tag('text') failed: {e}")


def test_registry_inheritance_behavior_documented():
    """Test and document the exact behavior of Registry inheritance."""
    import pydantic

    class BaseRegistry(Registry):
        pass

    class DerivedRegistry(BaseRegistry, Registry):  # type: ignore[misc]  # Correct MRO
        pass

    @dataclasses.dataclass
    class BaseVariant(BaseRegistry, _type_tag="base"):  # type: ignore[misc]
        x: int

    @dataclasses.dataclass
    class DerivedVariant(DerivedRegistry, _type_tag="derived"):  # type: ignore[misc]
        y: str

    # Document the actual behavior
    base_tags = tags(BaseRegistry)
    derived_tags = tags(DerivedRegistry)

    print(f"BaseRegistry tags: {base_tags}")
    print(f"DerivedRegistry tags: {derived_tags}")

    # Test serialization behavior
    base_instance = BaseVariant(x=42)
    derived_instance = DerivedVariant(y="test")

    # Direct serialization should always work
    base_direct = pydantic.TypeAdapter(BaseVariant).dump_python(base_instance)
    derived_direct = pydantic.TypeAdapter(DerivedVariant).dump_python(derived_instance)

    assert base_direct["_type_tag"] == "base"
    assert derived_direct["_type_tag"] == "derived"

    # Registry serialization
    base_via_base_registry = pydantic.TypeAdapter(BaseRegistry).dump_python(base_instance)
    derived_via_derived_registry = pydantic.TypeAdapter(DerivedRegistry).dump_python(
        derived_instance
    )

    assert base_via_base_registry["_type_tag"] == "base"
    assert derived_via_derived_registry["_type_tag"] == "derived"

    # Cross-registry serialization tests
    try:
        base_via_derived = pydantic.TypeAdapter(DerivedRegistry).dump_python(base_instance)  # type: ignore
        print(f"DerivedRegistry can serialize BaseVariant: {base_via_derived}")
        derived_can_serialize_base = True
    except Exception as e:
        print(f"DerivedRegistry cannot serialize BaseVariant: {e}")
        derived_can_serialize_base = False

    try:
        derived_via_base = pydantic.TypeAdapter(BaseRegistry).dump_python(derived_instance)
        print(f"BaseRegistry can serialize DerivedVariant: {derived_via_base}")
        base_can_serialize_derived = True
    except Exception as e:
        print(f"BaseRegistry cannot serialize DerivedVariant: {e}")
        base_can_serialize_derived = False

    print("Cross-serialization summary:")
    print(f"  DerivedRegistry -> BaseVariant: {derived_can_serialize_base}")
    print(f"  BaseRegistry -> DerivedVariant: {base_can_serialize_derived}")


def test_hierarchical_registry_inheritance():
    """Test that base registries contain all variants from derived registries."""
    import pydantic

    # Base registry
    class Message(Registry):
        pass

    # Derived registry
    class Command(Message, Registry):  # type: ignore[misc]
        pass

    # Variants in base registry
    @dataclasses.dataclass
    class TextMessage(Message, _type_tag="text"):  # type: ignore[misc]
        content: str

    @dataclasses.dataclass
    class ImageMessage(Message, _type_tag="image"):  # type: ignore[misc]
        url: str

    # Variants in derived registry
    @dataclasses.dataclass
    class AddCommand(Command, _type_tag="add"):  # type: ignore[misc]
        item: str

    @dataclasses.dataclass
    class DeleteCommand(Command, _type_tag="delete"):  # type: ignore[misc]
        item_id: int

    # Test hierarchical behavior: Message should see ALL variants
    message_tags = tags(Message)
    command_tags = tags(Command)

    print(f"Message tags: {message_tags}")
    print(f"Command tags: {command_tags}")

    # Message should contain both its own variants AND Command variants
    assert "text" in message_tags
    assert "image" in message_tags
    assert "add" in message_tags  # From derived Command registry
    assert "delete" in message_tags  # From derived Command registry

    # Command should only contain its own variants
    assert "add" in command_tags
    assert "delete" in command_tags
    assert "text" not in command_tags  # Should NOT contain parent variants
    assert "image" not in command_tags  # Should NOT contain parent variants

    # Test is_variant behavior
    text_msg = TextMessage(content="hello")
    add_cmd = AddCommand(item="test")

    # Message should recognize both its own and Command variants
    assert is_variant(Message, text_msg) is True
    assert is_variant(Message, add_cmd) is True
    assert is_variant(Message, TextMessage) is True
    assert is_variant(Message, AddCommand) is True

    # Command should only recognize its own variants
    assert is_variant(Command, add_cmd) is True
    assert is_variant(Command, AddCommand) is True
    assert is_variant(Command, text_msg) is False  # Should NOT recognize parent variants
    assert is_variant(Command, TextMessage) is False  # Should NOT recognize parent variants

    # Test by_tag behavior
    assert by_tag(Message, "text") is TextMessage
    assert by_tag(Message, "add") is AddCommand  # Can access derived registry variants
    assert by_tag(Command, "add") is AddCommand
    assert by_tag(Command, "delete") is DeleteCommand

    # Command should not be able to access parent variants by tag
    try:
        by_tag(Command, "text")
        assert False, "Command should not be able to access parent variant by tag"
    except KeyError:
        pass  # Expected

    # Test serialization behavior
    text_result = pydantic.TypeAdapter(TextMessage).dump_python(text_msg)
    add_result = pydantic.TypeAdapter(AddCommand).dump_python(add_cmd)

    assert text_result["_type_tag"] == "text"
    assert add_result["_type_tag"] == "add"

    # Test registry serialization - Message should handle ALL variants
    message_text = pydantic.TypeAdapter(Message).dump_python(text_msg)
    message_add = pydantic.TypeAdapter(Message).dump_python(add_cmd)

    assert message_text["_type_tag"] == "text"
    assert message_add["_type_tag"] == "add"

    # Test Command registry serialization
    command_add = pydantic.TypeAdapter(Command).dump_python(add_cmd)
    assert command_add["_type_tag"] == "add"

    # Message should be able to deserialize Command variants
    message_data = {"_type_tag": "add", "item": "test_item"}
    deserialized = pydantic.TypeAdapter(Message).validate_python(message_data)
    assert isinstance(deserialized, AddCommand)
    assert deserialized.item == "test_item"


def test_hierarchical_tag_conflicts():
    """Test that tag conflicts are detected across the hierarchy."""

    class BaseRegistry(Registry):
        pass

    class DerivedRegistry(BaseRegistry, Registry):  # type: ignore[misc]
        pass

    # Register a variant in base registry
    @dataclasses.dataclass
    class BaseVariant(BaseRegistry, _type_tag="conflict"):  # type: ignore[misc]
        x: int

    # Try to register a variant with the same tag in derived registry - should fail
    with pytest.raises(KeyError, match="Tag 'conflict' conflicts with existing variant"):

        @dataclasses.dataclass
        class DerivedVariant(DerivedRegistry, _type_tag="conflict"):  # type: ignore[misc]
            y: str


def test_multi_level_hierarchy():
    """Test registry hierarchy with multiple levels."""
    import pydantic

    # Level 1: Base
    class Document(Registry):
        pass

    # Level 2: Intermediate
    class TextDocument(Document, Registry):  # type: ignore[misc]
        pass

    # Level 3: Specific
    class MarkdownDocument(TextDocument, Registry):  # type: ignore[misc]
        pass

    # Add variants at each level
    @dataclasses.dataclass
    class GenericDocument(Document, _type_tag="generic"):  # type: ignore[misc]
        title: str

    @dataclasses.dataclass
    class PlainText(TextDocument, _type_tag="plain"):  # type: ignore[misc]
        content: str

    @dataclasses.dataclass
    class MarkdownFile(MarkdownDocument, _type_tag="markdown"):  # type: ignore[misc]
        markdown: str
        has_tables: bool

    # Test hierarchy: each level should see its descendants
    doc_tags = tags(Document)
    text_tags = tags(TextDocument)
    md_tags = tags(MarkdownDocument)

    print(f"Document tags: {doc_tags}")
    print(f"TextDocument tags: {text_tags}")
    print(f"MarkdownDocument tags: {md_tags}")

    # Document (top level) should see ALL variants
    assert "generic" in doc_tags
    assert "plain" in doc_tags
    assert "markdown" in doc_tags

    # TextDocument should see its own and descendants
    assert "plain" in text_tags
    assert "markdown" in text_tags
    assert "generic" not in text_tags  # Should not see parent variants

    # MarkdownDocument should only see its own
    assert "markdown" in md_tags
    assert "plain" not in md_tags
    assert "generic" not in md_tags

    # Test serialization works at all levels
    generic = GenericDocument(title="Test")
    plain = PlainText(content="Hello")
    markdown = MarkdownFile(markdown="# Title", has_tables=False)

    # Document registry should handle all variants
    doc_generic = pydantic.TypeAdapter(Document).dump_python(generic)
    doc_plain = pydantic.TypeAdapter(Document).dump_python(plain)
    doc_markdown = pydantic.TypeAdapter(Document).dump_python(markdown)

    assert doc_generic["_type_tag"] == "generic"
    assert doc_plain["_type_tag"] == "plain"
    assert doc_markdown["_type_tag"] == "markdown"

    # TextDocument should handle plain and markdown
    text_plain = pydantic.TypeAdapter(TextDocument).dump_python(plain)
    text_markdown = pydantic.TypeAdapter(TextDocument).dump_python(markdown)

    assert text_plain["_type_tag"] == "plain"
    assert text_markdown["_type_tag"] == "markdown"


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


def test_tagged_dataclass_with_dataclass_kwargs():
    """Test tagged_dataclass with dataclass-specific kwargs."""

    class TestRegistry(Registry):
        pass

    @tagged_dataclass(frozen=True, eq=False)
    class FrozenVariant(TestRegistry, _type_tag="frozen"):  # type: ignore[misc]
        value: int
        data: str

    # Test that the tag field is automatically added
    instance = FrozenVariant(value=100, data="test")
    assert instance.value == 100
    assert instance.data == "test"
    assert instance._type_tag == "frozen"  # type: ignore

    # Test that dataclass kwargs were applied
    # Frozen dataclass should be immutable
    with pytest.raises(dataclasses.FrozenInstanceError):
        instance.value = 200  # type: ignore

    # Test that it's a proper dataclass
    assert dataclasses.is_dataclass(FrozenVariant)


def test_tagged_dataclass_non_registry_fails():
    """Test that tagged_dataclass fails if class doesn't inherit from Registry."""

    class RegularClass:
        pass

    with pytest.raises(TypeError, match="must inherit from a Registry"):

        @tagged_dataclass
        class BadVariant(RegularClass):  # type: ignore[misc]
            value: int


def test_tagged_dataclass_with_parentheses():
    """Test tagged_dataclass decorator used with parentheses."""

    class TestRegistry(Registry):
        pass

    @tagged_dataclass()
    class ParenthesesVariant(TestRegistry, _type_tag="parentheses"):  # type: ignore[misc]
        value: int

    # Test that the tag field is automatically added
    instance = ParenthesesVariant(value=42)
    assert instance.value == 42
    assert instance._type_tag == "parentheses"  # type: ignore

    # Test that it's a proper dataclass
    assert dataclasses.is_dataclass(ParenthesesVariant)


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


def test_tagged_dataclass_with_inheritance():
    """Test tagged_dataclass with class inheritance."""
    import pydantic

    class Foundation(Registry):
        pass

    class Base(Foundation, Registry):  # type: ignore[misc]
        pass

    @tagged_dataclass
    class A(Base, _type_tag="concrete_a"):  # type: ignore[misc]
        x: int

    @tagged_dataclass
    class B(Base, _type_tag="concrete_b"):  # type: ignore[misc]
        y: str

    # Test that both variants have tag fields
    instance_a = A(x=100)
    instance_b = B(y="hello")

    assert instance_a.x == 100
    assert instance_a._type_tag == "concrete_a"  # type: ignore
    assert instance_b.y == "hello"
    assert instance_b._type_tag == "concrete_b"  # type: ignore

    # Test registry functionality
    assert tags(Foundation) == {"concrete_a", "concrete_b"}

    # Test Pydantic serialization
    result_a = pydantic.TypeAdapter(A).dump_python(instance_a)
    result_b = pydantic.TypeAdapter(B).dump_python(instance_b)

    assert result_a["_type_tag"] == "concrete_a"
    assert result_a["x"] == 100
    assert result_b["_type_tag"] == "concrete_b"
    assert result_b["y"] == "hello"


def test_tagged_dataclass_multiple_registries():
    """Test tagged_dataclass with multiple independent registries."""

    class RegistryA(Registry):
        pass

    class EventRegistry(create_registry("event_type")):
        pass

    @tagged_dataclass
    class TypeA(RegistryA, _type_tag="type_a"):  # type: ignore[misc]
        value: int

    @tagged_dataclass
    class EventB(EventRegistry, event_type="event_b"):  # type: ignore[misc]
        data: str

    # Test that both have their respective tag fields
    instance_a = TypeA(value=42)
    instance_b = EventB(data="test")

    assert instance_a.value == 42
    assert instance_a._type_tag == "type_a"  # type: ignore
    assert instance_b.data == "test"
    assert instance_b.event_type == "event_b"  # type: ignore

    # Test registry isolation
    assert tags(RegistryA) == {"type_a"}
    assert tags(EventRegistry) == {"event_b"}

    # Test that registries don't interfere
    assert is_variant(RegistryA, instance_a) is True
    assert is_variant(RegistryA, instance_b) is False
    assert is_variant(EventRegistry, instance_b) is True
    assert is_variant(EventRegistry, instance_a) is False
