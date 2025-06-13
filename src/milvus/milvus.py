#!/usr/bin/env python3
# File: src.milvus.py
"""Milvus API Implementation

This module provides a robust, extensible, and maintainable interface to the Milvus vector database using Python.
It integrates core functionality for managing collections, vectors, indexes, and embeddings, with support for
asynchronous operations, configuration management, security, and error handling. The implementation employs
several design patterns (Singleton, Factory, Builder, Strategy, Command, Template Method, Facade) to ensure
flexibility and reusability.

Key Features:
- Asynchronous Milvus operations (create, insert, search, delete, etc.)
- Support for multiple embedding types and models
- Configuration management via JSON or environment variables
- Basic security with encryption and authentication
- Comprehensive logging and error handling with retries
- Design patterns for extensibility and maintainability

Example Usage:
=============

```python

import asyncio
from milvus_api import MilvusAPI
>>>
async def main():
   async with ConnectAPI(
           alias="test_db",
           user="root",
           password="Milvus",
           host="10.1.0.99",
           port="19530",
           timeout=10,
           **{"db_name": "test_db"}
       ) as connect_api:
   api = MilvusAPI()
    # Create a collection
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
    ]
    api.create_collection("test_collection", fields, "test_db")
    # Insert data
    entities = [{"vector": [0.1] * 128} for _ in range(10)]
    api.insert("test_collection", entities, timeout="test_db")
    # Search
    results = api.search("test_collection", [[0.1] * 128], "vector", {"metric_type": "COSINE"}, 5)
    print(f"Search results: {results}")
    # Clean up
    api.drop_collection("test_collection", "test_db")

asyncio.run(main())

```
"""
import datetime
from collections.abc import Callable
from typing import Any

import numpy as np
from pymilvus import (
    Collection,
    CollectionSchema,
    FieldSchema,
    MilvusException,
)

from src.logger import getLogger as GetLogger
from src.milvus.admin import AdminAPI
from src.milvus.collection import CollectionAPI
from src.milvus.data import DataImportAPI
from src.milvus.embedding import EmbeddingAPI
from src.milvus.exceptions import MilvusAPIError
from src.milvus.index import IndexAPI
from src.milvus.interfaces import IConnectAPI
from src.milvus.monitor import MonitorAPI
from src.milvus.partition import PartitionAPI
from src.milvus.search import SearchAPI
from src.milvus.stats import StatAPI
from src.milvus.vector import VectorAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)


# Implementation Classes

class MilvusAPI:
    """Facade class integrating all Milvus APIs for a unified interface.

    Provides a simplified API for interacting with Milvus, supporting operations like
    collection management, vector operations, searches, and administration.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.
        _collection_api (CollectionAPI): The collection API instance.
        _vector_api (VectorAPI): The vector API instance.
        _search_api (SearchAPI): The search API instance.
        _index_api (IndexAPI): The index API instance.
        _partition_api (PartitionAPI): The partition API instance.
        _stat_api (StatAPI): The statistics API instance.
        _monitor_api (MonitorAPI): The monitoring API instance.
        _embedding_api (EmbeddingAPI): The embedding API instance.
        _admin_api (AdminAPI): The admin API instance.
        _data_import_api (DataImportAPI): The data import API instance.

    Methods:
        create_collection: Creates a new collection.
        drop_collection: Drops a collection.
        insert: Inserts entities into a collection.
        delete: Deletes entities from a collection.
        search: Searches for vectors in a collection.
        create_index: Creates an index on a field.
        drop_index: Drops an index from a field.
        create_partition: Creates a partition in a collection.
        drop_partition: Drops a partition from a collection.
        get_collection_stats: Gets collection statistics.
        get_monitor_info: Gets server monitoring information.
        generate_embeddings: Generates embeddings for data.
        create_user: Creates a new user.
        list_users: Lists all users.
        import_data: Imports data into a collection.

    Example:
        ```python
        async def main():
            async with ConnectAPI(host="localhost", port="19530") as connect_api:
                api = MilvusAPI(connect_api)
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
                ]
                api.create_collection("test_collection", fields, dimension=128)
                api.drop_collection("test_collection")
        asyncio.run(main())
        ```

    Raises:
        MilvusAPIError: If any operation fails.
        MilvusValidationError: If input parameters are invalid.

    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Ensures a singleton instance of ConnectAPI.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            ConnectAPI: The singleton instance.

        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            log.info(f"New MilvusAPI instance created @ {datetime.datetime.now()}")
        else:
            log.info(f"Using existing MilvusAPI instance created @ {datetime.datetime.now()}")
        return cls._instance

    def __init__(self, connect_api: IConnectAPI):
        """Initializes MilvusAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): Connection API instance.

        """
        if not hasattr(self, '_initialized') or not self._initialized:
            self._connect_api = connect_api
            self._collection_api = CollectionAPI(connect_api)
            self._vector_api = VectorAPI(connect_api)
            self._search_api = SearchAPI(connect_api)
            self._index_api = IndexAPI(connect_api)
            self._partition_api = PartitionAPI(connect_api)
            self._stat_api = StatAPI(connect_api)
            self._monitor_api = MonitorAPI(connect_api)
            self._embedding_api = EmbeddingAPI(connect_api)
            self._admin_api = AdminAPI(connect_api)
            self._data_import_api = DataImportAPI(connect_api)
            self._initialized = True
            log.info("MilvusAPI initialized...")
        else:
            log.warning("MilvusAPI instance already exists. Using existing parameters.")

    @async_log_decorator
    async def create_collection(self, collection_name: str,
                                fields: list[FieldSchema],
                                database_name: str = "default",
                                dimension: int | None = None,
                                primary_field_name: str = "id",
                                id_type: str = "int",
                                vector_field_name: str = "vector",
                                metric_type: str = "COSINE",
                                auto_id: bool = False,
                                timeout: float | None = None,
                                schema: CollectionSchema | None = None,
                                index_params: dict | None = None, **kwargs) -> Collection:
        """Creates a new collection.

        Args:
            collection_name (str): Name of the collection.
            fields (List[FieldSchema]): Field schemas.
            database_name (str): Database name. Defaults to "default".
            dimension (int | None): Vector dimension if auto-added.
            primary_field_name (str): Primary key name. Defaults to "id".
            id_type (str): Primary key type. Defaults to "int".
            vector_field_name (str): Vector field name. Defaults to "vector".
            metric_type (str): Index metric type. Defaults to "COSINE".
            auto_id (bool): Auto-generate IDs. Defaults to False.
            timeout (float | None): Operation timeout.
            schema (CollectionSchema | None): Pre-defined schema.
            index_params (Dict | None): Index parameters.
            **kwargs: Additional arguments.

        Returns:
            Collection: Created collection object.

        Raises:
            MilvusAPIError: If creation fails.

        """
        try:
            return await self._collection_api.create_collection(
                collection_name=collection_name,
                fields=fields,
                database_name=database_name,
                dimension=dimension,
                primary_field_name=primary_field_name,
                id_type=id_type,
                vector_field_name=vector_field_name,
                metric_type=metric_type,
                auto_id=auto_id,
                timeout=timeout,
                schema=schema,
                index_params=index_params,
                **kwargs
            )
        except MilvusException as e:
            log.error(f"Failed to create collection: {e}")
            raise MilvusAPIError(f"Collection creation failed: {e}")

    @async_log_decorator
    async def drop_collection(self, collection_name: str, timeout: float = 10) -> dict[str, str]:
        """Drops a collection.

        Args:
            collection_name (str): Name of the collection.
            timeout (float): Operation timeout. Defaults to 10.

        Returns:
            Dict[str, str]: Status of the drop operation.

        """
        return await self._collection_api.drop_collection(collection_name, timeout=timeout)

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
            Dict: Insertion result.

        """
        return await self._vector_api.insert(collection_name, entities, partition_name, database_name)

    @async_log_decorator
    def delete(self, collection_name: str, expr: str, partition_name: str | None = None,
                     database_name: str = "default") -> None:
        """Deletes entities from a collection.

        Args:
            collection_name (str): Name of the collection.
            expr (str): Expression to filter entities for deletion.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        """
        self._vector_api.delete(collection_name, expr, partition_name, database_name)

    @async_log_decorator
    async def search(self, collection_name: str, data: list[list[float]], anns_field: str, search_params: dict[str, Any],
                     limit: int, expr: str | None = None, output_fields: list[str] | None = None,
                     partition_names: list[str] | None = None, database_name: str = "default",
                     rerank: bool = False, **kwargs) -> list[dict]:
        """Searches for vectors in a collection.

        Args:
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            search_params (Dict[str, Any]): Search parameters.
            limit (int): Maximum number of results.
            expr (Optional[str]): Filter expression. Defaults to None.
            output_fields (Optional[List[str]]): Fields to return. Defaults to None.
            partition_names (Optional[List[str]]): Partitions to search. Defaults to None.
            database_name (str): Database name. Defaults to "default".
            rerank (bool): Whether to rerank results. Defaults to False.
            **kwargs: Additional search parameters.

        Returns:
            List[Dict]: Search results.

        """
        return await self._search_api.search(
            collection_name,
            data,
            anns_field,
            search_params,
            limit,
            expr,
            output_fields,
            partition_names,
            database_name,
            rerank,
            **kwargs)

    @async_log_decorator
    def create_index(self,
                           collection_name: str, field_name: str,
                           index_params: dict, database_name: str = "default", **kwargs) -> None:
        """Creates an index on a field.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field to index.
            index_params (Dict): Index parameters.
            database_name (str): Database name. Defaults to "default".
            **kwargs: Additional index parameters.

        """
        self._index_api.create_index(collection_name, field_name, index_params, database_name, **kwargs)

    @async_log_decorator
    def drop_index(self, collection_name: str, field_name: str, database_name: str = "default") -> None:
        """Drops an index from a field.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field with the index.
            database_name (str): Database name. Defaults to "default".

        """
        self._index_api.drop_index(collection_name, field_name, database_name)

    @async_log_decorator
    def create_partition(self, collection_name: str, partition_name: str, database_name: str = "default") -> None:
        """Creates a partition in a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        """
        self._partition_api.create_partition(collection_name, partition_name, database_name)

    @async_log_decorator
    def drop_partition(self, collection_name: str, partition_name: str, database_name: str = "default") -> None:
        """Drops a partition from a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        """
        self._partition_api.drop_partition(collection_name, partition_name, database_name)

    @async_log_decorator
    def get_collection_stats(self, collection_name: str, database_name: str = "default") -> dict[str, Any]:
        """Gets collection statistics.

        Args:
            collection_name (str): Name of the collection.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict[str, Any]: Collection statistics.

        """
        return self._stat_api.get_collection_stats(collection_name, database_name)

    @async_log_decorator
    def get_monitor_info(self) -> dict[str, Any]:
        """Gets server monitoring information.

        Returns:
            Dict[str, Any]: Monitoring metrics.

        """
        return self._monitor_api.get_monitor_info()

    @async_log_decorator
    def generate_embeddings(self, data: list[Any], embedding_model: Callable[[list[Any]], np.ndarray],
                                  embedding_type: str = "float", batch_size: int = 32) -> np.ndarray:
        """Generates embeddings for data.

        Args:
            data (List[Any]): Data to embed.
            embedding_model (Callable[[List[Any]], np.ndarray]): Model to generate embeddings.
            embedding_type (str): Type of embeddings. Defaults to "float".
            batch_size (int): Number of items per batch. Defaults to 32.

        Returns:
            np.ndarray: Generated embeddings.

        """
        return self._embedding_api.generate_embeddings(data, embedding_model, embedding_type, batch_size)

    @async_log_decorator
    def create_user(self, username: str, password: str) -> None:
        """Creates a new user.

        Args:
            username (str): Username for the new user.
            password (str): Password for the new user.

        """
        self._admin_api.create_user(username, password)

    @async_log_decorator
    def list_users(self) -> list[str]:
        """Lists all users.

        Returns:
            List[str]: List of usernames.

        """
        return self._admin_api.list_users()

    @async_log_decorator
    def import_data(self, collection_name: str, file_path: str, database_name: str = "default") -> None:
        """Imports data into a collection.

        Args:
            collection_name (str): Name of the collection.
            file_path (str): Path to the data file.
            database_name (str): Database name. Defaults to "default".

        """
        self._data_import_api.import_data(collection_name, file_path, database_name)




