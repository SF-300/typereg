# TypeReg

A powerful Python library for creating type registries with Pydantic integration. TypeReg allows you to create tagged union types that can be serialized and deserialized with proper type discrimination.

## Features

- **Type Registries**: Create registries of related types with automatic tag-based discrimination
- **Pydantic Integration**: Seamless serialization/deserialization with Pydantic models
- **Custom Tag Keywords**: Use custom field names for type discrimination
- **Hierarchical Registries**: Support for nested and inherited registries
- **Dataclass Support**: Automatic tag field injection for dataclasses
- **Type Safety**: Full type checking support with proper generic annotations

## Installation

```bash
pip install typereg
```

## Quick Start

```python
from dataclasses import dataclass
from typereg import Registry, tagged_dataclass
from pydantic import BaseModel

# Create a registry
class MessageRegistry(Registry):
    pass

# Define tagged variants
@tagged_dataclass
class TextMessage(MessageRegistry, _type_tag="text"):
    content: str
    sender: str

@tagged_dataclass  
class ImageMessage(MessageRegistry, _type_tag="image"):
    url: str
    caption: str

# Use in Pydantic models
class Conversation(BaseModel):
    messages: list[MessageRegistry]

# Serialize/deserialize with automatic type discrimination
data = {
    "messages": [
        {"_type_tag": "text", "content": "Hello!", "sender": "Alice"},
        {"_type_tag": "image", "url": "https://example.com/pic.jpg", "caption": "Sunset"}
    ]
}

conversation = Conversation.model_validate(data)
# conversation.messages[0] is automatically a TextMessage instance
# conversation.messages[1] is automatically an ImageMessage instance
```

## Custom Tag Keywords

```python
from typereg import create_registry

# Create registry with custom tag field name
DocumentRegistry = create_registry("doc_type")

@tagged_dataclass
class PDFDocument(DocumentRegistry, doc_type="pdf"):
    file_path: str
    pages: int

@tagged_dataclass
class WordDocument(DocumentRegistry, doc_type="docx"):
    file_path: str
    word_count: int
```

## Registry Hierarchy

```python
# Base registry
class Document(Registry):
    pass

# Derived registry inherits from base
class TextDocument(Document, Registry):
    pass

@tagged_dataclass
class PlainText(TextDocument, _type_tag="plain"):
    content: str

@tagged_dataclass  
class Markdown(TextDocument, _type_tag="markdown"):
    content: str
    has_tables: bool

# Base registry sees all variants from derived registries
assert "plain" in tags(Document)
assert "markdown" in tags(Document)
```

## API Reference

### Core Functions

- `Registry`: Base class for creating type registries
- `create_registry(tag_kwarg)`: Factory for creating registries with custom tag keywords
- `tagged_dataclass`: Decorator that automatically adds tag fields to dataclasses
- `tags(registry)`: Get all registered tags for a registry
- `by_tag(registry, tag)`: Get class by tag name
- `tag_of(registry, obj_or_cls)`: Get tag for a given object or class
- `is_variant(registry, obj_or_cls)`: Check if object/class is a registered variant

## Requirements

- Python 3.10+
- Pydantic v2
- typing-extensions (for older Python versions)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
