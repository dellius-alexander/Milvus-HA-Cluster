from pymilvus import Collection, MilvusException

from src.milvus.exceptions import MilvusValidationError, MilvusAPIError
from src.milvus.interfaces import IPartitionAPI, IConnectAPI
from src.utils import async_log_decorator

from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)


class PartitionAPI(IPartitionAPI):
    """
    Manages partitions within Milvus collections.

    Implements the IPartitionAPI interface to handle partition creation and deletion.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_partition: Creates a partition in a collection.
        drop_partition: Drops a partition from a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = PartitionAPI(connect_api)
        api.create_partition("test_collection", "partition1")
        ```

    Raises:
        MilvusAPIError: If partition operations fail.
        MilvusValidationError: If input parameters are invalid.
    """
    def __init__(self, connect_api: IConnectAPI):
        """Initializes PartitionAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    def create_partition(self, collection_name: str, partition_name: str, database_name: str = "default"):
        """Creates a partition in a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If partition creation fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not partition_name or not isinstance(partition_name, str):
            raise MilvusValidationError("Partition name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            partition =  collection.create_partition(partition_name=partition_name)
            log.info(f"Created partition {partition_name} in {collection_name}, \nPartition: {partition}")
        except MilvusException as e:
            log.error(f"Failed to create partition: {e}")
            raise MilvusAPIError(f"Partition creation failed: {e}")

    @async_log_decorator
    def drop_partition(self, collection_name: str, partition_name: str, database_name: str = "default"):
        """Drops a partition from a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If partition drop fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not partition_name or not isinstance(partition_name, str):
            raise MilvusValidationError("Partition name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.drop_partition(partition_name=partition_name)
            log.info(f"Dropped partition {partition_name} from {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to drop partition: {e}")
            raise MilvusAPIError(f"Partition drop failed: {e}")
