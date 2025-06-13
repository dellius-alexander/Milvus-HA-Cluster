import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pymilvus import (
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusException,
)
from src.logger import getLogger
from src.milvus.collection import CollectionAPI
from src.milvus.connect import ConnectAPI
from src.milvus.embedding import EmbeddingAPI
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.index import IndexAPI
from src.milvus.milvus import MilvusAPI
from src.milvus.monitor import MonitorAPI
from src.milvus.partition import PartitionAPI
from src.milvus.search import SearchAPI
from src.milvus.stats import StatAPI
from src.milvus.vector import VectorAPI

log = getLogger(__name__)

# Fixture for ConnectAPI with context manager
@pytest.fixture
def connect_api():
    with patch('pymilvus.connections') as mock_connections:
        with ConnectAPI(
            alias="test_alias",
            user="root",
            password="Milvus",
            host="10.1.0.99",
            port="19530",
            timeout=10
        ).connection() as connect_api:
            yield connect_api

# Fixture for sample collection schema
@pytest.fixture
def collection_schema():
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
    ]
    return CollectionSchema(fields=fields, description="Test collection")

# Fixture for temporary directory
@pytest.fixture
def tmp_path(tmpdir):
    temp_dir = tmpdir.mkdir("temp")
    yield str(temp_dir)

# Cleanup temporary directory after tests
@pytest.fixture(autouse=True)
def cleanup_temp_dir(tmp_path):
    if os.path.exists(tmp_path):
        for file in os.listdir(tmp_path):
            file_path = os.path.join(tmp_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(tmp_path)

# Cleanup vector database after tests
@pytest.fixture
def cleanup_test_alias(connect_api):
    collection_api = CollectionAPI(connect_api)
    try:
        collections = collection_api.list_collections()
        for collection in collections:
            collection_api.drop_collection(collection)
    except Exception as e:
        log.warning(f"Failed to clean up collections: {e}")

# Test ConnectAPI
def test_connect_api_initialization(connect_api):
    """Tests ConnectAPI initialization with correct parameters."""
    assert connect_api._alias == "test_alias"
    assert connect_api._initialized is True
    assert connect_api._timeout == 10

def test_connect_api_context_manager(connect_api):
    """Tests ConnectAPI context manager for connection and disconnection."""
    with patch('pymilvus.connections.disconnect') as mock_disconnect:
        with ConnectAPI(alias="test_alias").connection() as conn:
            assert conn._alias == "test_alias"
        mock_disconnect.assert_called_with("test_alias")

def test_connect_api_failure():
    """Tests ConnectAPI failure handling with invalid connection."""
    with patch('pymilvus.connections.connect', side_effect=MilvusException(message="Connection failed")):
        with pytest.raises(MilvusAPIError, match="Connection failed"):
            ConnectAPI(alias="fail_alias")

# Test CollectionAPI
def test_collection_api_create_collection(connect_api, collection_schema):
    """Tests creating a new collection."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.has_collection', return_value=False), \
         patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value = MagicMock()
        result = collection_api.create_collection("test_collection", collection_schema.fields)
        assert isinstance(result, MagicMock)
        mock_collection.assert_called()

def test_collection_api_create_existing_collection(connect_api, collection_schema):
    """Tests handling of existing collection."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.has_collection', return_value=True), \
         patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value = MagicMock()
        result = collection_api.create_collection("test_collection", collection_schema.fields)
        assert isinstance(result, MagicMock)
        mock_collection.assert_called_with(name="test_collection")

def test_collection_api_list_collections(connect_api):
    """Tests listing all collections."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.list_collections', return_value=["col1", "col2"]):
        collections = collection_api.list_collections()
        assert collections == ["col1", "col2"]

def test_collection_api_has_collection(connect_api):
    """Tests checking if a collection exists."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.has_collection', return_value=True):
        assert collection_api.has_collection("test_collection") is True

def test_collection_api_drop_collection(connect_api):
    """Tests dropping a collection."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.has_collection', side_effect=[True, False]), \
         patch('pymilvus.utility.drop_collection') as mock_drop:
        result = collection_api.drop_collection("test_collection")
        assert result == {"message": "Collection test_collection dropped", "status": "success"}
        mock_drop.assert_called_with("test_collection")

def test_collection_api_drop_nonexistent_collection(connect_api):
    """Tests dropping a non-existent collection."""
    collection_api = CollectionAPI(connect_api)
    with patch('pymilvus.utility.has_collection', return_value=False):
        result = collection_api.drop_collection("test_collection")
        assert result == {"message": "Collection test_collection does not exist", "status": "failed"}

def test_collection_api_invalid_inputs(connect_api):
    """Tests input validation in CollectionAPI."""
    collection_api = CollectionAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        collection_api.create_collection("", [])
    with pytest.raises(MilvusValidationError, match="Fields must be a non-empty list of FieldSchema objects"):
        collection_api.create_collection("test_collection", [])

# Test VectorAPI
def test_vector_api_create_vector(connect_api):
    """Tests inserting a single vector."""
    vector_api = VectorAPI(connect_api)
    vector = [0.1] * 128
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.schema.fields = [
            MagicMock(name="id", dtype=DataType.INT64, is_primary=True),
            MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
        ]
        mock_collection.return_value.insert.return_value.primary_keys = [1]
        mock_collection.return_value.flush = MagicMock()
        vector_id = vector_api.create_vector("test_collection", vector)
        assert vector_id == 1
        mock_collection.return_value.insert.assert_called()

def test_vector_api_delete_vector(connect_api):
    """Tests deleting a vector by ID."""
    vector_api = VectorAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.delete = MagicMock()
        mock_collection.return_value.flush = MagicMock()
        vector_api.delete_vector("test_collection", 1)
        mock_collection.return_value.delete.assert_called_with("id in [1]")

def test_vector_api_invalid_inputs(connect_api):
    """Tests input validation in VectorAPI."""
    vector_api = VectorAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        vector_api.create_vector("", [0.1] * 128)
    with pytest.raises(MilvusValidationError, match="Vector must be a non-empty list of numbers"):
        vector_api.create_vector("test_collection", [])
    with pytest.raises(MilvusValidationError, match="Vector dimension"):
        with patch('pymilvus.Collection') as mock_collection:
            mock_collection.return_value.schema.fields = [
                MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=64)
            ]
            vector_api.create_vector("test_collection", [0.1] * 128)

# Test IndexAPI
def test_index_api_create_index(connect_api):
    """Tests creating an index on a field."""
    index_api = IndexAPI(connect_api)
    index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}}
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.create_index = MagicMock()
        index_api.create_index("test_collection", "vector", index_params)
        mock_collection.return_value.create_index.assert_called_with(field_name="vector", index_params=index_params)

def test_index_api_drop_index(connect_api):
    """Tests dropping an index from a field."""
    index_api = IndexAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.drop_index = MagicMock()
        index_api.drop_index("test_collection", "vector")
        mock_collection.return_value.drop_index.assert_called_with(field_name="vector")

def test_index_api_invalid_inputs(connect_api):
    """Tests input validation in IndexAPI."""
    index_api = IndexAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        index_api.create_index("", "vector", {})
    with pytest.raises(MilvusValidationError, match="Index parameters must be a non-empty dictionary"):
        index_api.create_index("test_collection", "vector", {})

# Test PartitionAPI
def test_partition_api_create_partition(connect_api):
    """Tests creating a partition."""
    partition_api = PartitionAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.create_partition = MagicMock()
        partition_api.create_partition("test_collection", "test_partition")
        mock_collection.return_value.create_partition.assert_called_with(partition_name="test_partition")

def test_partition_api_delete_partition(connect_api):
    """Tests deleting a partition."""
    partition_api = PartitionAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.drop_partition = MagicMock()
        partition_api.delete_partition("test_collection", "test_partition")
        mock_collection.return_value.drop_partition.assert_called_with(partition_name="test_partition")

def test_partition_api_invalid_inputs(connect_api):
    """Tests input validation in PartitionAPI."""
    partition_api = PartitionAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        partition_api.create_partition("", "test_partition")
    with pytest.raises(MilvusValidationError, match="Partition name must be a non-empty string"):
        partition_api.create_partition("test_collection", "")

# Test StatAPI
def test_stat_api_get_collection_stats(connect_api):
    """Tests retrieving collection statistics with caching."""
    stat_api = StatAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.stats = {"row_count": 100}
        stats1 = stat_api.get_collection_stats("test_collection")
        stats2 = stat_api.get_collection_stats("test_collection")
        assert stats1 == {"row_count": 100}
        assert stats2 == stats1  # Should be cached
        mock_collection.assert_called_once()

def test_stat_api_invalid_inputs(connect_api):
    """Tests input validation in StatAPI."""
    stat_api = StatAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        stat_api.get_collection_stats("")

# Test SearchAPI (Async)
@pytest.mark.asyncio
async def test_search_api_search_vectors(connect_api):
    """Tests async vector search."""
    search_api = SearchAPI(connect_api)
    vectors = [[0.1] * 128]
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.search.return_value = [{"id": 1, "distance": 0.1}]
        mock_collection.return_value.load = MagicMock()
        results = await search_api.search_vectors("test_collection", vectors, "vector", limit=10, partition_names=["part1"])
        assert results == [{"id": 1, "distance": 0.1}]
        mock_collection.return_value.search.assert_called_with(
            data=vectors,
            anns_field="vector",
            search_params={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=10,
            partition_names=["part1"]
        )

@pytest.mark.asyncio
async def test_search_api_invalid_inputs(connect_api):
    """Tests input validation in SearchAPI."""
    search_api = SearchAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        await search_api.search_vectors("", [[0.1] * 128], "vector")
    with pytest.raises(MilvusValidationError, match="Vectors must be a non-empty list of number lists"):
        await search_api.search_vectors("test_collection", [], "vector")
    with pytest.raises(MilvusValidationError, match="Field name must be a non-empty string"):
        await search_api.search_vectors("test_collection", [[0.1] * 128], "")

# Test BatchAPI (Async)
class BatchAPI:
    pass


@pytest.mark.asyncio
async def test_batch_api_batch_insert_vectors(connect_api):
    """Tests async batch vector insertion with and without partition."""
    batch_api = BatchAPI(connect_api)
    entities = [{"id": 1, "vector": [0.1] * 128}, {"id": 2, "vector": [0.2] * 128}]
    with patch('pymilvus.Collection') as mock_collection:
        # Mock schema for validation
        mock_collection.return_value.schema.fields = [
            MagicMock(name="id", dtype=DataType.INT64, is_primary=True),
            MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
        ]
        # Mock partition to return the same collection for simplicity
        mock_collection.return_value.partition.return_value = mock_collection.return_value
        mock_collection.return_value.insert.return_value.primary_keys = [1, 2]
        mock_collection.return_value.flush = MagicMock()
        primary_keys = await batch_api.batch_insert_vectors("test_collection", "part1", entities)
        assert primary_keys == [1, 2]
        mock_collection.return_value.insert.assert_called_once()
        mock_collection.return_value.partition.assert_called_once_with("part1")
        # Test without partition
        primary_keys = await batch_api.batch_insert_vectors("test_collection", None, entities)
        assert primary_keys == [1, 2]
        mock_collection.return_value.insert.assert_called()

@pytest.mark.asyncio
async def test_batch_api_batch_delete_vectors(connect_api):
    """Tests async batch vector deletion."""
    batch_api = BatchAPI(connect_api)
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.delete = MagicMock()
        mock_collection.return_value.flush = MagicMock()
        await batch_api.batch_delete_vectors("test_collection", [1, 2])
        mock_collection.return_value.delete.assert_called_once_with("id in [1, 2]")
        mock_collection.return_value.flush.assert_called_once()

@pytest.mark.asyncio
async def test_batch_api_invalid_inputs(connect_api):
    """Tests input validation in BatchAPI."""
    batch_api = BatchAPI(connect_api)
    # Test empty collection name
    with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
        await batch_api.batch_insert_vectors("", None, [{"id": 1, "vector": [0.1] * 128}])
    # Test empty entities
    with pytest.raises(MilvusValidationError, match="Entities must be a non-empty list of dictionaries"):
        await batch_api.batch_insert_vectors("test_collection", None, [])
    # Test missing required fields
    with pytest.raises(MilvusValidationError, match="Entity missing required fields"):
        with patch('pymilvus.Collection') as mock_collection:
            mock_collection.return_value.schema.fields = [
                MagicMock(name="id", dtype=DataType.INT64, is_primary=True),
                MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            await batch_api.batch_insert_vectors("test_collection", None, [{"id": 1}])
    # Test invalid vector dimension
    with pytest.raises(MilvusValidationError, match="Vector dimension"):
        with patch('pymilvus.Collection') as mock_collection:
            mock_collection.return_value.schema.fields = [
                MagicMock(name="id", dtype=DataType.INT64, is_primary=True),
                MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=64)
            ]
            await batch_api.batch_insert_vectors("test_collection", None, [{"id": 1, "vector": [0.1] * 128}])
    # Test invalid partition name
    with pytest.raises(MilvusValidationError, match="Partition name must be a non-empty string"):
        await batch_api.batch_insert_vectors("test_collection", "", [{"id": 1, "vector": [0.1] * 128}])

# # Test TableAPI
# def test_table_api_get_table_row_count(connect_api):
#     """Tests retrieving table row count with caching."""
#     table_api = TableAPI(connect_api)
#     with patch('pymilvus.Collection') as mock_collection:
#         mock_collection.return_value.num_entities = 100
#         count1 = table_api.get_table_row_count("test_collection")
#         count2 = table_api.get_table_row_count("test_collection")
#         assert count1 == 100
#         assert count2 == count1  # Should be cached
#         mock_collection.assert_called_once()
#
# def test_table_api_invalid_inputs(connect_api):
#     """Tests input validation in TableAPI."""
#     table_api = TableAPI(connect_api)
#     with pytest.raises(MilvusValidationError, match="Collection name must be a non-empty string"):
#         table_api.get_table_row_count("")

# Test MonitorAPI
def test_monitor_api_get_monitor_info(connect_api):
    """Tests retrieving monitor information."""
    monitor_api = MonitorAPI(connect_api)
    mock_metrics = {
        "server_version": "2.3.0",
        "connection_status": True,
        "timestamp": "2025-04-22T10:00:00.123456",
        "collections": {
            "test_collection": {
                "num_entities": 1000,
                "has_index": True,
                "partitions": 2
            }
        },
        "collection_count": 1
    }
    with patch('pymilvus.utility.get_server_version', return_value="2.3.0"), \
         patch('pymilvus.connections.has_connection', return_value=True), \
         patch('pymilvus.utility.list_collections', return_value=["test_collection"]), \
         patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.num_entities = 1000
        mock_collection.return_value.has_index.return_value = True
        mock_collection.return_value.partitions = [MagicMock(), MagicMock()]
        metrics = monitor_api.get_monitor_info()
        assert metrics["server_version"] == "2.3.0"
        assert metrics["connection_status"] is True
        assert metrics["collection_count"] == 1
        assert metrics["collections"]["test_collection"]["num_entities"] == 1000
        assert "timestamp" in metrics

def test_monitor_api_get_monitor_info_partial_failure(connect_api):
    """Tests monitor info retrieval with partial collection failure."""
    monitor_api = MonitorAPI(connect_api)
    with patch('pymilvus.utility.get_server_version', return_value="2.3.0"), \
         patch('pymilvus.connections.has_connection', return_value=True), \
         patch('pymilvus.utility.list_collections', return_value=["test_collection"]), \
         patch('pymilvus.Collection', side_effect=MilvusException(message="Collection error")):
        metrics = monitor_api.get_monitor_info()
        assert metrics["server_version"] == "2.3.0"
        assert metrics["collection_count"] == 1
        assert metrics["collections"] == {}

# Test EmbeddingAPI
def test_embedding_api_generate_embeddings(connect_api):
    """Tests embedding generation."""
    embedding_api = EmbeddingAPI(connect_api)
    data = ["text1", "text2"]
    def mock_embedding_model(data):
        return np.random.rand(len(data), 128)
    embeddings = embedding_api.generate_embeddings(data, mock_embedding_model, batch_size=1)
    assert embeddings.shape == (2, 128)
    assert np.all((embeddings >= 0) & (embeddings <= 1))

def test_embedding_api_invalid_inputs(connect_api):
    """Tests input validation in EmbeddingAPI."""
    embedding_api = EmbeddingAPI(connect_api)
    with pytest.raises(MilvusValidationError, match="Data must be a non-empty list"):
        embedding_api.generate_embeddings([], lambda x: np.array([]))
    with pytest.raises(MilvusValidationError, match="Embedding model must be a callable function"):
        embedding_api.generate_embeddings(["text1"], None)
    with pytest.raises(MilvusValidationError, match="Embedding model must return a NumPy array"):
        embedding_api.generate_embeddings(["text1"], lambda x: [0.1])

# Test MilvusAPI Facade
def test_milvus_api_create_collection(collection_schema):
    """Tests MilvusAPI collection creation."""
    with patch('pymilvus.utility.has_collection', return_value=False), \
         patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value = MagicMock()
        milvus_api = MilvusAPI()
        result = milvus_api.create_collection("test_collection", collection_schema.fields)
        assert isinstance(result, MagicMock)
        mock_collection.assert_called()

@pytest.mark.asyncio
async def test_milvus_api_insert_and_search():
    """Tests MilvusAPI vector insertion and async search."""
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.schema.fields = [
            MagicMock(name="id", dtype=DataType.INT64, is_primary=True),
            MagicMock(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
        ]
        mock_collection.return_value.insert.return_value.primary_keys = [1]
        mock_collection.return_value.flush = MagicMock()
        mock_collection.return_value.search.return_value = [{"id": 1, "distance": 0.1}]
        mock_collection.return_value.load = MagicMock()
        milvus_api = MilvusAPI()
        vector_id = milvus_api.insert_vector("test_collection", [0.1] * 128, partition_name="part1")
        results = await milvus_api.search_vectors("test_collection", [[0.1] * 128], "vector", partition_names=["part1"])
        assert vector_id == 1
        assert results == [{"id": 1, "distance": 0.1}]

def test_milvus_api_get_row_count():
    """Tests MilvusAPI row count retrieval."""
    with patch('pymilvus.Collection') as mock_collection:
        mock_collection.return_value.num_entities = 100
        milvus_api = MilvusAPI()
        count = milvus_api.get_row_count("test_collection")
        assert count == 100

def test_milvus_api_generate_embeddings():
    """Tests MilvusAPI embedding generation."""
    milvus_api = MilvusAPI()
    data = ["text1", "text2"]
    def mock_embedding_model(data):
        return np.random.rand(len(data), 128)
    embeddings = milvus_api.generate_embeddings(data, mock_embedding_model, batch_size=1)
    assert embeddings.shape == (2, 128)
    assert np.all((embeddings >= 0) & (embeddings <= 1))

# # Test ConfigurationLoader
# def test_configuration_loader(tmp_path):
#     """Tests loading configuration from a file."""
#     config_file = os.path.join(tmp_path, "config.ini")
#     config_content = """[Milvus]
# host = 10.1.0.99
# port = 19530
# user = root
# password = Milvus
# alias = test_alias
# """
#     with open(config_file, "w") as file:
#         file.write(config_content)
#     loader = ConfigurationLoader(config_file)
#     assert isinstance(loader.config, configparser.ConfigParser)
#     assert loader.config["Milvus"]["host"] == "10.1.0.99"
#
# def test_configuration_loader_failure(tmp_path):
#     """Tests handling of missing configuration file."""
#     config_file = os.path.join(tmp_path, "nonexistent.ini")
#     with pytest.raises(MilvusAPIError, match="Configuration load failed"):
#         ConfigurationLoader(config_file)
#
# # Test DataGenerator
# def test_data_generator_vectors():
#     """Tests generating synthetic vectors."""
#     generator = DataGenerator()
#     vectors = generator.generate_vectors("float", 128, 10)
#     assert vectors.shape == (10, 128)
#     assert np.all((vectors >= 0) & (vectors <= 1))
#
# def test_data_generator_invalid_type():
#     """Tests handling of invalid vector type."""
#     generator = DataGenerator()
#     with pytest.raises(MilvusValidationError, match="Unsupported vector type"):
#         generator.generate_vectors("invalid", 128, 10)


if __name__ == "__main__":
    pytest.main(["-v"])
