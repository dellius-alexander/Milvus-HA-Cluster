import configparser
import csv
import datetime
import json
import logging
import random
import time
from typing import List, Dict, Any, Union, Optional
import jsonlines
import numpy as np
from pymilvus import (
    FieldSchema, CollectionSchema, DataType, Collection, utility, connections,
    MilvusException
)
import mysql.connector as mysql_connector
from myLogger.Logger import getLogger as GetLogger

log = GetLogger(__name__)


class MilvusAPIError(Exception):
    """Custom exception for Milvus API errors."""
    pass


# 1. ConnectAPI (Singleton Pattern)
class ConnectAPI:
    """Manages connection to the Milvus vector database."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConnectAPI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, alias: str = "default", user: str = "milvus", password: str = "developer",
                 host: str = "127.0.0.1", port: str = "19530", **kwargs):
        if not getattr(self, '_initialized', False):
            try:
                self._alias = alias
                self._connect(alias=alias, user=user, password=password, host=host, port=port, **kwargs)
                self._initialized = True
                log.info(f"Connected to Milvus at {host}:{port} with alias {alias}")
            except MilvusException as e:
                log.error(f"Failed to connect to Milvus: {e}")
                raise MilvusAPIError(f"Connection failed: {e}")

    def _connect(self, alias: str, user: str, password: str, host: str, port: str, **kwargs) -> None:
        """Establishes connection to Milvus."""
        connections.connect(
            alias=alias, user=user, password=password, host=host, port=port, **kwargs
        )

    def disconnect(self) -> None:
        """Disconnects from Milvus."""
        try:
            connections.disconnect(self._alias)
            log.info(f"Disconnected from Milvus, alias: {self._alias}")
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")


# 2. CollectionAPI
class CollectionAPI:
    """Manages Milvus collections."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def create_collection(self, collection_name: str, fields: List[FieldSchema], **kwargs) -> Collection:
        """Creates a new collection in Milvus."""
        try:
            if utility.has_collection(collection_name):
                log.info(f"Collection {collection_name} already exists")
                return Collection(name=collection_name)

            if not fields:
                raise MilvusAPIError("Fields must be specified for new collection")

            schema = CollectionSchema(
                fields=fields,
                description=kwargs.get("description", ""),
                segment_row_limit=kwargs.get("segment_row_limit", 1000000),
                auto_id=kwargs.get("auto_id", True)
            )
            collection = Collection(name=collection_name, schema=schema, **kwargs)
            log.info(f"Created collection {collection_name}")
            return collection
        except MilvusException as e:
            log.error(f"Failed to create collection {collection_name}: {e}")
            raise MilvusAPIError(f"Collection creation failed: {e}")

    def list_collections(self) -> List[str]:
        """Lists all collections in Milvus."""
        try:
            collections = utility.list_collections()
            return collections
        except MilvusException as e:
            log.error(f"Failed to list collections: {e}")
            raise MilvusAPIError(f"List collections failed: {e}")

    def has_collection(self, collection_name: str) -> bool:
        """Checks if a collection exists."""
        try:
            return utility.has_collection(collection_name)
        except MilvusException as e:
            log.error(f"Failed to check collection {collection_name}: {e}")
            raise MilvusAPIError(f"Check collection failed: {e}")

    def drop_collection(self, collection_name: str) -> Dict[str, str]:
        """Drops a collection from Milvus."""
        try:
            if not self.has_collection(collection_name):
                return {"message": f"Collection {collection_name} does not exist", "status": "failed"}

            utility.drop_collection(collection_name)
            if not self.has_collection(collection_name):
                log.info(f"Dropped collection {collection_name}")
                return {"message": f"Collection {collection_name} dropped", "status": "success"}
            return {"message": f"Collection {collection_name} still exists", "status": "failed"}
        except MilvusException as e:
            log.error(f"Failed to drop collection {collection_name}: {e}")
            raise MilvusAPIError(f"Drop collection failed: {e}")


# 3. VectorAPI
class VectorAPI:
    """Manages vector operations in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def create_vector(self, collection_name: str, vector: List[float], id: Optional[int] = None) -> int:
        """Inserts a single vector into a collection."""
        try:
            collection = Collection(collection_name)
            data = [vector] if id is None else [[id], [vector]]
            entities = collection.insert(data)
            collection.flush()
            log.info(f"Inserted vector into {collection_name}, ID: {entities.primary_keys[0]}")
            return entities.primary_keys[0]
        except MilvusException as e:
            log.error(f"Failed to insert vector into {collection_name}: {e}")
            raise MilvusAPIError(f"Vector insertion failed: {e}")

    def delete_vector(self, collection_name: str, vector_id: int) -> None:
        """Deletes a vector by ID from a collection."""
        try:
            collection = Collection(collection_name)
            collection.delete(f"id in [{vector_id}]")
            collection.flush()
            log.info(f"Deleted vector {vector_id} from {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to delete vector {vector_id} from {collection_name}: {e}")
            raise MilvusAPIError(f"Vector deletion failed: {e}")


# 4. IndexAPI
class IndexAPI:
    """Manages indexes in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def create_index(self, collection_name: str, field_name: str, index_params: Dict, **kwargs) -> None:
        """Creates an index on a field in a collection."""
        try:
            collection = Collection(collection_name)
            collection.create_index(field_name=field_name, index_params=index_params, **kwargs)
            log.info(f"Created index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to create index on {field_name} in {collection_name}: {e}")
            raise MilvusAPIError(f"Index creation failed: {e}")

    def drop_index(self, collection_name: str, field_name: str) -> None:
        """Drops an index from a field in a collection."""
        try:
            collection = Collection(collection_name)
            collection.drop_index(field_name=field_name)
            log.info(f"Dropped index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to drop index on {field_name} in {collection_name}: {e}")
            raise MilvusAPIError(f"Index drop failed: {e}")


# 5. PartitionAPI
class PartitionAPI:
    """Manages partitions in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def create_partition(self, collection_name: str, partition_name: str, **kwargs) -> None:
        """Creates a partition in a collection."""
        try:
            collection = Collection(collection_name)
            collection.create_partition(partition_name=partition_name, **kwargs)
            log.info(f"Created partition {partition_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to create partition {partition_name} in {collection_name}: {e}")
            raise MilvusAPIError(f"Partition creation failed: {e}")

    def delete_partition(self, collection_name: str, partition_name: str) -> None:
        """Deletes a partition from a collection."""
        try:
            collection = Collection(collection_name)
            collection.drop_partition(partition_name=partition_name)
            log.info(f"Deleted partition {partition_name} from {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to delete partition {partition_name} from {collection_name}: {e}")
            raise MilvusAPIError(f"Partition deletion failed: {e}")


# 6. StatAPI
class StatAPI:
    """Retrieves statistics from Milvus collections."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Retrieves statistics for a collection."""
        try:
            collection = Collection(collection_name)
            stats = collection.stats
            log.info(f"Retrieved stats for {collection_name}")
            return stats
        except MilvusException as e:
            log.error(f"Failed to retrieve stats for {collection_name}: {e}")
            raise MilvusAPIError(f"Stats retrieval failed: {e}")


# 7. SearchAPI
class SearchAPI:
    """Handles vector search operations in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def search_vectors(self, collection_name: str, vectors: List[List[float]],
                       field_name: str, limit: int = 10, **kwargs) -> List[Dict]:
        """Searches for similar vectors in a collection."""
        try:
            collection = Collection(collection_name)
            collection.load()
            search_params = kwargs.get("search_params", {"metric_type": "L2", "params": {"nprobe": 10}})
            results = collection.search(
                data=vectors,
                anns_field=field_name,
                param=search_params,
                limit=limit,
                **kwargs
            )
            log.info(f"Performed search in {collection_name}")
            return results
        except MilvusException as e:
            log.error(f"Failed to search in {collection_name}: {e}")
            raise MilvusAPIError(f"Search failed: {e}")


# 8. BatchAPI
class BatchAPI:
    """Manages batch operations in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def batch_insert_vectors(self, collection_name: str, partition_name: Optional[str],
                             entities: List[Dict], **kwargs) -> List[int]:
        """Inserts multiple vectors into a collection."""
        try:
            collection = Collection(collection_name)
            if partition_name:
                collection = collection.partition(partition_name)

            data = []
            for entity in entities:
                data.append([entity[field] for field in entity.keys()])

            mr = collection.insert(data, **kwargs)
            collection.flush()
            log.info(f"Inserted {len(entities)} vectors into {collection_name}")
            return mr.primary_keys
        except MilvusException as e:
            log.error(f"Failed to batch insert into {collection_name}: {e}")
            raise MilvusAPIError(f"Batch insert failed: {e}")

    def batch_delete_vectors(self, collection_name: str, ids: List[int]) -> None:
        """Deletes multiple vectors by IDs from a collection."""
        try:
            collection = Collection(collection_name)
            collection.delete(f"id in {ids}")
            collection.flush()
            log.info(f"Deleted {len(ids)} vectors from {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to batch delete from {collection_name}: {e}")
            raise MilvusAPIError(f"Batch delete failed: {e}")


# 9. TableAPI
class TableAPI:
    """Manages table-related operations in Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def get_table_row_count(self, collection_name: str) -> int:
        """Retrieves the row count of a collection."""
        try:
            collection = Collection(collection_name)
            count = collection.num_entities
            log.info(f"Retrieved row count {count} for {collection_name}")
            return count
        except MilvusException as e:
            log.error(f"Failed to retrieve row count for {collection_name}: {e}")
            raise MilvusAPIError(f"Row count retrieval failed: {e}")


# 10. MonitorAPI
class MonitorAPI:
    """Retrieves monitoring information from Milvus."""

    def __init__(self, connect_api: ConnectAPI):
        self._connect_api = connect_api

    def get_monitor_info(self) -> Dict[str, Any]:
        """Retrieves monitoring information from Milvus."""
        try:
            metrics = utility.get_server_metrics()
            log.info("Retrieved Milvus server metrics")
            return metrics
        except MilvusException as e:
            log.error(f"Failed to retrieve monitor info: {e}")
            raise MilvusAPIError(f"Monitor info retrieval failed: {e}")


# Facade Pattern for MilvusAPI
class MilvusAPI:
    """Facade providing a simplified interface to Milvus operations."""

    def __init__(self, alias: str = "default", user: str = "milvus", password: str = "developer",
                 host: str = "127.0.0.1", port: str = "19530", **kwargs):
        self._connect_api = ConnectAPI(alias, user, password, host, port, **kwargs)
        self._collection_api = CollectionAPI(self._connect_api)
        self._vector_api = VectorAPI(self._connect_api)
        self._index_api = IndexAPI(self._connect_api)
        self._partition_api = PartitionAPI(self._connect_api)
        self._stat_api = StatAPI(self._connect_api)
        self._search_api = SearchAPI(self._connect_api)
        self._batch_api = BatchAPI(self._connect_api)
        self._table_api = TableAPI(self._connect_api)
        self._monitor_api = MonitorAPI(self._connect_api)

    def create_collection(self, collection_name: str, fields: List[FieldSchema], **kwargs) -> Collection:
        return self._collection_api.create_collection(collection_name, fields, **kwargs)

    def drop_collection(self, collection_name: str) -> Dict[str, str]:
        return self._collection_api.drop_collection(collection_name)

    def insert_vector(self, collection_name: str, vector: List[float], id: Optional[int] = None) -> int:
        return self._vector_api.create_vector(collection_name, vector, id)

    def search_vectors(self, collection_name: str, vectors: List[List[float]],
                       field_name: str, limit: int = 10, **kwargs) -> List[Dict]:
        return self._search_api.search_vectors(collection_name, vectors, field_name, limit, **kwargs)

    def batch_insert(self, collection_name: str, partition_name: Optional[str],
                     entities: List[Dict], **kwargs) -> List[int]:
        return self._batch_api.batch_insert_vectors(collection_name, partition_name, entities, **kwargs)

    def get_row_count(self, collection_name: str) -> int:
        return self._table_api.get_table_row_count(collection_name)

    def get_monitor_info(self) -> Dict[str, Any]:
        return self._monitor_api.get_monitor_info()


# Support Classes (kept minimal for brevity, but improved)
class ConfigurationLoader:
    """Loads configuration settings from a file."""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> configparser.ConfigParser:
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            log.info(f"Loaded configuration from {self.config_file}")
            return config
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise MilvusAPIError(f"Configuration load failed: {e}")


class DataGenerator:
    """Generates synthetic data for testing."""

    def generate_vectors(self, vector_type: str, vector_size: int, vector_count: int) -> np.ndarray:
        try:
            if vector_type == 'binary':
                return np.random.randint(0, 2, (vector_count, vector_size))
            elif vector_type == 'float':
                return np.random.rand(vector_count, vector_size)
            elif vector_type == 'int':
                return np.random.randint(0, 1000, (vector_count, vector_size))
            elif vector_type == 'string':
                return np.random.randint(0, 1000, (vector_count, vector_size)).astype(str)
            raise ValueError(f"Unsupported vector type: {vector_type}")
        except Exception as e:
            log.error(f"Failed to generate vectors: {e}")
            raise MilvusAPIError(f"Vector generation failed: {e}")

