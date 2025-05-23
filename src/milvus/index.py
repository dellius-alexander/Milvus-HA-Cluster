from typing import Dict

from pymilvus import Collection, MilvusException

from src.milvus.exceptions import MilvusValidationError, MilvusAPIError
from src.milvus.interfaces import IIndexAPI, IConnectAPI
from src.logger import getLogger as GetLogger
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)

class IndexAPI(IIndexAPI):
    """
    Handles index creation and deletion in Milvus.

    Implements the IIndexAPI interface to manage indexes on collection fields.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_index: Creates an index on a field.
        drop_index: Drops an index from a field.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = IndexAPI(connect_api)
        api.create_index("test_collection", "vector", {"index_type": "IVF_FLAT"})
        ```

    Raises:
        MilvusAPIError: If index operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes IndexAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    def create_index(self, collection_name: str, field_name: str,
                           index_params: Dict, database_name: str = "default", **kwargs):
        """Creates an index on a field in a collection.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field to index.
            index_params (Dict): Index parameters.
            database_name (str): Database name. Defaults to "default".
            **kwargs: Additional index arguments.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If index creation fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not field_name or not isinstance(field_name, str):
            raise MilvusValidationError("Field name must be a non-empty string")
        if not index_params or not isinstance(index_params, dict):
            raise MilvusValidationError("Index parameters must be a non-empty dictionary")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.create_index(field_name=field_name, index_params=index_params, **kwargs)
            log.info(f"Created index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to create index: {e}")
            raise MilvusAPIError(f"Index creation failed: {e}")

    @async_log_decorator
    def drop_index(self, collection_name: str, field_name: str, database_name: str = "default"):
        """Drops an index from a field in a collection.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field with the index.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If index drop fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not field_name or not isinstance(field_name, str):
            raise MilvusValidationError("Field name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.drop_index(field_name=field_name)
            log.info(f"Dropped index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to drop index: {e}")
            raise MilvusAPIError(f"Index drop failed: {e}")
