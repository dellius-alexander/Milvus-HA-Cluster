import datetime
from typing import Dict, Any

from pymilvus import Collection, MilvusException
from pymilvus.orm import utility

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError
from src.milvus.interfaces import IMonitorAPI, IConnectAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)


class MonitorAPI(IMonitorAPI):
    """
    Provides monitoring information for the Milvus server.

    Implements the IMonitorAPI interface to retrieve server metrics.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        get_monitor_info: Retrieves monitoring information.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = MonitorAPI(connect_api)
        info = api.get_monitor_info()
        ```

    Raises:
        MilvusAPIError: If monitoring information retrieval fails.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes MonitorAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    def get_monitor_info(self) -> Dict[str, Any]:
        """Gets monitoring information for the Milvus server.

        Returns:
            Dict[str, Any]: Monitoring metrics including server version and collection stats.

        Raises:
            MilvusAPIError: If info retrieval fails.
        """
        try:
            server_version = utility.get_server_version()
            connection_status = self._connect_api.connect_api is not None
            collections = self._connect_api.connect_api.list_collections()
            collection_stats = {}
            for col_name in collections:
                try:
                    collection = Collection(col_name, using=self._connect_api._alias)
                    stats = {
                        "num_entities": collection.num_entities,
                        "has_index": collection.has_index(),
                        "partitions": len(collection.partitions)
                    }
                    collection_stats[col_name] = stats
                except MilvusException as e:
                    log.warning(f"Failed to retrieve stats for collection {col_name}: {e}")
            metrics = {
                "server_version": server_version,
                "connection_status": connection_status,
                "timestamp": datetime.datetime.now().isoformat(),
                "collections": collection_stats,
                "collection_count": len(collections)
            }
            log.info(f"Retrieved Milvus server metrics: version={server_version}, collections={len(collections)}")
            return metrics
        except MilvusException as e:
            log.error(f"Failed to retrieve monitor info: {e}")
            raise MilvusAPIError(f"Monitor info retrieval failed: {e}")
