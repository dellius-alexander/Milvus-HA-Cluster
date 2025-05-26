import asyncio
import os
import unittest

import pytest
from pymilvus import FieldSchema, DataType, Collection

from src.logger import getLogger as GetLogger
from src.milvus.connect import ConnectAPI
from src.milvus.milvus import MilvusAPI

# Logging setup
log = GetLogger(__name__)


# Unit Tests
class TestMilvusAPI(unittest.TestCase):

    async def setUp(self):
        self.api = None
        with ConnectAPI(
                alias=os.environ["MILVUS_DB"],
                uri=os.environ["MILVUS_DB_URI"],
                user=os.environ["MILVUS_USER"],
                password=os.environ["MILVUS_PASSWORD"],
                db_name=os.environ["MILVUS_DB"],
                token=os.environ["MILVUS_DB_TOKEN"],
                timeout=10
    ) as connect_api:
            log.info(f"ConnectAPI: \n {connect_api}")
            # Initialize the MilvusAPI with the connection
            self.api = MilvusAPI(connect_api=connect_api)


    def test_create_collection(self):
        async def run_test():
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            collection = await self.api.create_collection(
                collection_name="test_collection",
                fields=fields,
                dimension=128,
                index_params={"index_type": "IVF_FLAT", "params": {"nlist": 1024}},
                database_name="test_db"
            )
            self.assertIsInstance(collection, Collection)
        asyncio.run(run_test())

    def test_insert(self):
        async def run_test():
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            await self.api.create_collection("test_collection", fields, "test_db")
            ids = await self.api.insert("test_collection", [{"vector": [0.1] * 128}], None, "test_db")
            self.assertTrue(isinstance(ids, list))
        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main(["-v", __file__])