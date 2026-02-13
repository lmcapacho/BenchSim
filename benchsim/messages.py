"""
Message types for the messaging system.
"""
from enum import Enum

class MessageType(Enum):
    """Enumeration of message types."""
    ERROR = "error"
    SUCCESS = "success"
    LOG = "log"
    WARNING = "warning"

def create_message(message_type, text, extras=None, data=None):
    """Create a standardized message dictionary with optional extra actions."""
    if isinstance(message_type, MessageType):
        message_type = message_type.value
    return {
        "type": message_type,
        "message": text,
        "extras": extras or [],
        "data": data or {},
    }

def is_error(message):
    """Check if the message is an error."""
    return message.get("type") == MessageType.ERROR.value

def is_success(message):
    """Check if the message is a success."""
    return message.get("type") == MessageType.SUCCESS.value

def is_log(message):
    """Check if the message is a log."""
    return message.get("type") == MessageType.LOG.value

def is_warning(message):
    """Check if the message is a warning."""
    return message.get("type") == MessageType.WARNING.value
