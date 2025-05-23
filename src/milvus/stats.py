from typing import Dict, Any

from pymilvus import Collection, MilvusException

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusValidationError, MilvusAPIError
from src.milvus.interfaces import IStatAPI, IConnectAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)


class StatAPI(IStatAPI):
    """
    Retrieves statistics for Milvus collections.

    Implements the IStatAPI interface to provide collection statistics.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        get_collection_stats: Retrieves statistics for a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = StatAPI(connect_api)
        stats = api.get_collection_stats("test_collection")
        ```

    Raises:
        MilvusAPIError: If statistics retrieval fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes StatAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    def get_collection_stats(self, collection_name: str, database_name: str = "default") -> Dict[str, Any]:
        """Gets statistics for a collection.

        Args:
            collection_name (str): Name of the collection.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict[str, Any]: Collection statistics.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If stats retrieval fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            stats = collection.stats
            log.info(f"Retrieved stats for {collection_name}")
            return stats
        except MilvusException as e:
            log.error(f"Failed to retrieve stats: {e}")
            raise MilvusAPIError(f"Stats retrieval failed: {e}")
