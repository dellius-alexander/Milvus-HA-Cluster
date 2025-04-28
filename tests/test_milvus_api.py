import asyncio
import unittest

from pymilvus import FieldSchema, DataType, Collection

from src.milvus import MilvusAPI


# Unit Tests
class TestMilvusAPI(unittest.TestCase):
    def setUp(self):
        self.api = MilvusAPI()

    def test_create_collection(self):
        async def run_test():
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            collection = await self.api.create_collection("test_collection", fields, "test_db")
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
