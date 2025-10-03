"""Model persistence using joblib."""

import io
import logging
from typing import Any

import joblib

logger = logging.getLogger(__name__)


def serialize_model(model: Any) -> bytes:
    """
    Serialize model to bytes using joblib.

    Args:
        model: Model object to serialize

    Returns:
        Serialized model bytes
    """
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=3)
    return buffer.getvalue()


def deserialize_model(blob: bytes) -> Any:
    """
    Deserialize model from bytes.

    Args:
        blob: Serialized model bytes

    Returns:
        Deserialized model object
    """
    buffer = io.BytesIO(blob)
    return joblib.load(buffer)
