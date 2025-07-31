import dataclasses
import functools
import typing as t

from .base import REGISTRY_STATE, SENTINEL
from .utils import get_existing_field_info, get_parent_registry_root


def _dataclass(cls: type | None = None, /, **dataclass_kwargs) -> t.Any:
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
        if target_cls not in REGISTRY_STATE:
            registry_root = get_parent_registry_root(target_cls)
            if registry_root is None:
                raise TypeError(
                    f"Class {target_cls.__name__} must inherit from a Registry to use @tagged_dataclass. "
                    f"Make sure your class inherits from a Registry class created with create_registry() "
                    f"or the default Registry."
                )

            registry_state = REGISTRY_STATE[registry_root]

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
            existing_annotation, existing_default = get_existing_field_info(
                target_cls, tag_kwarg
            )

            if existing_annotation is None and existing_default is SENTINEL:
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
    tagged_dataclass = _dataclass
