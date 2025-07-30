"""
Basic example demonstrating TypeReg usage with Pydantic.
"""

from pydantic import BaseModel

from typereg import Registry, tagged_dataclass


# Create a message registry
class Message(Registry):
    """Base registry for different message types."""
    pass


# Define message variants using tagged_dataclass
@tagged_dataclass
class TextMessage(Message, _type_tag="text"):
    content: str
    sender: str
    timestamp: int


@tagged_dataclass
class ImageMessage(Message, _type_tag="image"):
    url: str
    caption: str
    sender: str
    width: int
    height: int


@tagged_dataclass
class FileMessage(Message, _type_tag="file"):
    filename: str
    file_size: int
    sender: str
    mime_type: str


# Use in Pydantic models
class ChatRoom(BaseModel):
    name: str
    messages: list[Message]  # type: ignore[valid-type]


def main():
    """Demonstrate basic TypeReg usage."""

    # Create some messages
    messages_data = [
        {
            "_type_tag": "text",
            "content": "Hello everyone!",
            "sender": "Alice",
            "timestamp": 1642684800,
        },
        {
            "_type_tag": "image",
            "url": "https://example.com/sunset.jpg",
            "caption": "Beautiful sunset",
            "sender": "Bob",
            "width": 1920,
            "height": 1080,
        },
        {
            "_type_tag": "file",
            "filename": "document.pdf",
            "file_size": 1048576,
            "sender": "Charlie",
            "mime_type": "application/pdf",
        },
    ]

    # Create a chat room from the data
    chat_data = {"name": "General Chat", "messages": messages_data}

    chat_room = ChatRoom.model_validate(chat_data)

    # The messages are automatically deserialized to the correct types
    print(f"Chat room: {chat_room.name}")
    print(f"Number of messages: {len(chat_room.messages)}")

    for i, message in enumerate(chat_room.messages):
        print(f"\nMessage {i + 1}:")
        print(f"  Type: {type(message).__name__}")
        print(f"  Sender: {message.sender}")

        if isinstance(message, TextMessage):
            print(f"  Content: {message.content}")
            print(f"  Timestamp: {message.timestamp}")
        elif isinstance(message, ImageMessage):
            print(f"  URL: {message.url}")
            print(f"  Caption: {message.caption}")
            print(f"  Dimensions: {message.width}x{message.height}")
        elif isinstance(message, FileMessage):
            print(f"  Filename: {message.filename}")
            print(f"  Size: {message.file_size} bytes")
            print(f"  MIME type: {message.mime_type}")

    # Serialize back to JSON
    print("\nSerialized back to JSON:")
    print(chat_room.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
