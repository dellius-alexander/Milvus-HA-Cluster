from collections.abc import Callable
from typing import Any

import numpy as np

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.interfaces import IConnectAPI, IEmbeddingAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)

class EmbeddingAPI(IEmbeddingAPI):
    """Generates embeddings using a provided model for Milvus.

    Implements the IEmbeddingAPI interface to handle embedding generation.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        generate_embeddings: Generates embeddings for data.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = EmbeddingAPI(connect_api)
        embeddings = api.generate_embeddings(["text"], lambda x: np.array([[0.1] * 128]))
        ```

    Raises:
        MilvusAPIError: If embedding generation fails.
        MilvusValidationError: If input parameters are invalid.

    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes EmbeddingAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.

        """
        self._connect_api = connect_api

    @async_log_decorator
    def generate_embeddings(self, data: list[Any], embedding_model: Callable[[list[Any]], np.ndarray],
                                  embedding_type: str = "float", batch_size: int = 32) -> np.ndarray:
        """Generates embeddings for the provided data.

        Args:
            data (List[Any]): Data to embed (e.g., text, images).
            embedding_model (Callable[[List[Any]], np.ndarray]): Model to generate embeddings.
            embedding_type (str): Type of embeddings ("float" or "binary"). Defaults to "float".
            batch_size (int): Number of items per batch. Defaults to 32.

        Returns:
            np.ndarray: Generated embeddings.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If embedding generation fails.

        """
        if not data:
            raise MilvusValidationError("Data must be a non-empty list")
        if not callable(embedding_model):
            raise MilvusValidationError("Embedding model must be a callable function")
        if embedding_type not in ["float", "binary"]:
            raise MilvusValidationError(f"Unsupported embedding type: {embedding_type}")
        try:
            embeddings = []
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_embeddings = embedding_model(batch)
                if not isinstance(batch_embeddings, np.ndarray):
                    raise MilvusValidationError("Embedding model must return a NumPy array")
                if embedding_type == "binary":
                    batch_embeddings = (batch_embeddings > 0.5).astype(np.uint8)
                embeddings.append(batch_embeddings)
            result = np.concatenate(embeddings, axis=0)
            log.info(f"Generated embeddings for {len(data)} items")
            return result
        except Exception as e:
            log.error(f"Failed to generate embeddings: {e}")
            raise MilvusAPIError(f"Embedding generation failed: {e}")
