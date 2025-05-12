import asyncio
from pymilvus import FieldSchema, DataType

from src.milvus import ConnectAPI, MilvusAPI
from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)


async def main():
    try:
        async with ConnectAPI(
                alias="test_db",
                user="root",
                password="Milvus",
                host="10.1.0.99",
                port="19530",
                timeout=10
        ) as connect_api:
            log.info(f"Connecting to Milvus with alias: {connect_api._alias}")
            log.info(f"Connection parameters: {connect_api.__dict__}")
            log.info(f"Connecting to Milvus at {connect_api._host}:{connect_api._port}")
            log.info("Connected to Milvus successfully.")
            log.info(f"ConnectAPI: \n {connect_api}")
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
                dimension=128,
                index_params={"index_type": "IVF_FLAT", "params": {"nlist": 1024}},
                database_name="test_db"
            )
            log.info(f"Created collection: {collection}")
            entities = [{"vector": [0.1] * 128}]
            log.info(f"Inserting entities: {entities}")
            results = await api.insert(
                collection_name="test_collection",
                entities=entities)
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
    except Exception as e:
        log.error(f"An error occurred: {e}"
                  f"\n{e.__traceback__}")
        await connect_api.close()


# Example usage
if __name__ == "__main__":

    asyncio.run(main())

    # async with AsyncMilvusClientWrapper(
    #     uri=os.environ.get("MILVUS_URI"),
    #     user=os.environ.get("MILVUS_USER"),
    #     password=os.environ.get("MILVUS_PASSWD"),
    #     db_name=os.environ.get("MILVUS_DB"),
    #     host=os.environ.get("MILVUS_HOST"),
    #     port=int(os.environ.get("MILVUS_PORT")),
    #     token=os.environ.get("MILVUS_TOKEN"),
    #     timeout=os.environ.get("MILVUS_TIMEOUT")) as client:
    #     log.info("Connected to Milvus")
    #     # Example usage of the API
    #     await client.create_collection("test_collection", [
    #         FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    #         FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
    #     ])
    #     log.info(await client.has_collection("test_collection"))
    #     await client

