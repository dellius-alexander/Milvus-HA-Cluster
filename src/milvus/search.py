from typing import List, Dict, Any, Optional

from pymilvus import Collection, MilvusException

from src.milvus.exceptions import MilvusValidationError, MilvusAPIError
from src.milvus.interfaces import IStrategy, ISearchAPI, IConnectAPI
from src.utils import async_log_decorator
from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)


class SearchAPI(ISearchAPI):
    """
    Manages vector searches in Milvus with optional reranking.

    Implements the ISearchAPI interface to handle search operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        search: Performs a vector search in a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = SearchAPI(connect_api)
        results = api.search("test_collection", [[0.1] * 128], "vector", {"metric_type": "COSINE"}, 5)
        ```

    Raises:
        MilvusAPIError: If search operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes SearchAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    async def search(self,
                     collection_name: str, data: List[List[float]],
                     anns_field: str, param: Dict[str, Any],
                     limit: int, expr: Optional[str] = None,
                     output_fields: Optional[List[str]] = None,
                     partition_names: Optional[List[str]] = None,
                     database_name: str = "default",
                     rerank: bool = False, **kwargs) -> List[Dict]:
        """Performs a vector search in the specified collection.

        Args:
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            param (Dict[str, Any]): Search parameters (e.g., metric_type).
            limit (int): Maximum number of results.
            expr (Optional[str]): Filter expression. Defaults to None.
            output_fields (Optional[List[str]]): Fields to return. Defaults to None.
            partition_names (Optional[List[str]]): Partitions to search. Defaults to None.
            database_name (str): Database name. Defaults to "default".
            rerank (bool): Whether to rerank results by distance. Defaults to False.
            **kwargs: Additional search arguments.

        Returns:
            List[Dict]: Search results with IDs and distances.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If search fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not data or not all(isinstance(v, list) for v in data):
            raise MilvusValidationError("Data must be a non-empty list of lists")
        if not anns_field or not isinstance(anns_field, str):
            raise MilvusValidationError("ANNS field must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.load()
            # Search the database
            results = await self._connect_api.connect_api.search(
                collection_name=collection_name,
                data=data,
                anns_field=anns_field,
                search_params=param,
                limit=limit,
                filter=expr,
                output_fields=output_fields,
                partition_names=partition_names,
                db_name=database_name,
                **kwargs
            )
            # Get the results at index 0
            results = results[0]
            log.debug(f"Contents of results: {results}, "
                      f"\nAttributes of results: {dir(results)}, "
                      f"\nType of results: {type(results)}, "
                      f"\nLength of results: {len(results)}, "
                      f"\nContains distance: {'distance' in str(results)}")

            # Check if reranking is needed
            if rerank and "distance" in str(results):
                log.info(f"Reranking {len(results)} results by distance")
                results = self._rerank_results(results)

            log.info(f"Completed search in {collection_name}, \nResults: {results}")
            return results
        except MilvusException as e:
            log.error(f"Failed to search: {e}")
            raise MilvusAPIError(f"Search failed: {e}")

    @async_log_decorator
    def _rerank_results(self, results: List[Dict]) -> List[Dict]:
        """Reranks search results by distance.

        Args:
            results (List[Dict]): Original search results.

        Returns:
            List[Dict]: Reranked results.
        """
        return sorted(results, key=lambda x: x["distance"])


class SearchStrategy(IStrategy):
    """
    Strategy for searching data in Milvus collections.

    Implements the IStrategy interface to define search behavior.

    Methods:
        execute: Performs the search operation.

    Example:
        ```python
        strategy = SearchStrategy()
        api = SearchAPI(connect_api)
        result = strategy.execute(api, "test_collection", [[0.1] * 128], "vector", 5)
        ```

    Raises:
        MilvusAPIError: If the search operation fails.
        MilvusValidationError: If input parameters are invalid.
    """
    def execute(self,
                      api: ISearchAPI,
                      collection_name: str,
                      data: List[List[float]],
                      anns_field: str,
                      limit: int, **kwargs):
        """
        Performs the search operation.

        Args:
            api (ISearchAPI): The search API instance.
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            limit (int): Maximum number of results.
            **kwargs: Additional search parameters.

        Returns:
            Any: Result of the search operation.
       """
        return api.search(collection_name, data, anns_field, {"metric_type": "COSINE"}, limit, **kwargs)

