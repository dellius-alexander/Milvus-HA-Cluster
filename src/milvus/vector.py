from typing import Any

from pymilvus import Collection, MilvusException

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.interfaces import IConnectAPI, IVectorAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)

class VectorAPI(IVectorAPI):
    """Handles vector operations like insertion and deletion in Milvus.

    Implements the IVectorAPI interface to manage vector data.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        insert: Inserts entities into a collection.
        delete: Deletes entities from a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = VectorAPI(connect_api)
        api.insert("test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If vector operations fail.
        MilvusValidationError: If input parameters are invalid.

    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes VectorAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    async def insert(self, collection_name: str, entities: list[dict[str, Any]], partition_name: str | None = None,
                     database_name: str = "default") -> dict:
        """Inserts entities into a collection.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        Returns:
            List[int]: List of primary keys for inserted entities.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If insertion fails.

        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not entities or not all(isinstance(e, dict) for e in entities):
            raise MilvusValidationError("Entities must be a non-empty list of dictionaries")
        try:
            collection = Collection(
                name=collection_name,
                using=self._connect_api._db_name
            )
            # MR: MilvusResultS
            mr: dict = await self._connect_api.client.insert(
                collection_name=collection_name,
                data=entities,
                partition_name=partition_name,
                db_name=database_name
            )
            log.debug(f"Insert result: {mr}")
            collection.flush()
            log.info(f"Inserted {len(entities)} entities into {collection_name}")
            return mr
        except MilvusException as e:
            log.error(f"Failed to insert entities: {e}")
            raise MilvusAPIError(f"Insert failed: {e}")

    @async_log_decorator
    def delete(self, collection_name: str, expr: str, partition_name: str | None = None,
                     database_name: str = "default"):
        """Deletes entities from a collection based on an expression.

        Args:
            collection_name (str): Name of the collection.
            expr (str): Expression to filter entities for deletion.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If deletion fails.

        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not expr or not isinstance(expr, str):
            raise MilvusValidationError("Expression must be a non-empty string")
        try:
            self._connect_api.client.delete(
                collection_name=collection_name,
                expr=expr,
                partition_name=partition_name,
                db_name=database_name
            )
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.flush()
            log.info(f"Deleted entities from {collection_name} with expression: {expr}")
        except MilvusException as e:
            log.error(f"Failed to delete entities: {e}")
            raise MilvusAPIError(f"Delete failed: {e}")
