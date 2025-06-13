from pymilvus import MilvusException

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.interfaces import IConnectAPI, IDataImportAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)


class DataImportAPI(IDataImportAPI):
    """Handles data imports into Milvus collections.

    Implements the IDataImportAPI interface to manage data import operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        import_data: Imports data into a collection from a file.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = DataImportAPI(connect_api)
        api.import_data("test_collection", "data.json")
        ```

    Raises:
        MilvusAPIError: If data import fails.
        MilvusValidationError: If input parameters are invalid.

    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes DataImportAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.

        """
        self._connect_api = connect_api

    @async_log_decorator
    def import_data(self, collection_name: str, file_path: str, database_name: str = "default"):
        """Imports data into a collection from a file.

        Args:
            collection_name (str): Name of the collection.
            file_path (str): Path to the data file.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If import fails.

        """
        if not collection_name or not isinstance(collection_name, str) or not file_path or not isinstance(file_path, str):
            raise MilvusValidationError("Collection name and file path must be non-empty strings")
        try:
            self._connect_api.client.import_data(
                collection_name=collection_name,
                file_path=file_path,
                db_name=database_name
            )
            log.info(f"Imported data into {collection_name} from {file_path}")
        except MilvusException as e:
            log.error(f"Failed to import data: {e}")
            raise MilvusAPIError(f"Data import failed: {e}")
