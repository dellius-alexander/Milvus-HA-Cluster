import asyncio
import os

from pymilvus import DataType, FieldSchema
from src.logger import getLogger as GetLogger
from src.milvus.connect import ConnectAPI
from src.milvus.exceptions import MilvusAPIError
from src.milvus.milvus import MilvusAPI

# Logging setup
log = GetLogger(__name__)


async def main():
    try:
        connect_api = ConnectAPI(
            alias=os.environ["MILVUS_DB"],
            uri=os.environ["MILVUS_DB_URI"],
            user=os.environ["MILVUS_USER"],
            password=os.environ["MILVUS_PASSWORD"],
            db_name=os.environ["MILVUS_DB"],
            token=os.environ["MILVUS_DB_TOKEN"],
            timeout=30
        )
        with connect_api:
            log.info(f"Connected to Milvus successfully with {connect_api}")
            log.info(f"Connecting to Milvus with alias: {connect_api._alias}")
            log.info(f"Connection parameters: {connect_api.__dict__}")
            log.info(f"Connecting to Milvus at {connect_api._host}:{connect_api._port}")
            if connect_api.client is None:
                raise MilvusAPIError("Milvus client is not initialized")

            api = MilvusAPI(connect_api)
            log.info(f"MilvusAPI: \n {api}")
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True, description="id"),
                FieldSchema(
                    name="vector", dtype=DataType.FLOAT_VECTOR, dim=128, description="vector")
            ]
            log.info(f"Creating collection with fields: {fields}")
            collection = await api.create_collection(
                collection_name="test_collection",
                fields=fields,
                database_name="test_db",
                index_params={"index_type": "IVF_FLAT", "params": {"nlist": 1024}}
            )
            log.info(f"Created collection: {collection}")
            entities = [{"vector": [0.1] * 128}]
            log.info(f"Inserting entities: {entities}")
            results = await api.insert(
                collection_name="test_collection",
                entities=entities,
                database_name=os.environ["MILVUS_DB"],
            )
            log.info(f"Insert results: {results}")
            results = await api.search(
                collection_name="test_collection",
                data=[[0.1] * 128],
                anns_field="vector",
                search_params={"metric_type": "COSINE"},
                limit=10,
                rerank=True,
            )
            log.info(f"Search results: {results}")
            await api.drop_collection("test_collection")
    except MilvusAPIError as e:
        log.error(f"Milvus API error: {e}")
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise


# Example usage
if __name__ == "__main__":
    asyncio.run(main())


