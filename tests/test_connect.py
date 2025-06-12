import pytest
import os
from unittest import TestCase

from src.milvus.connect import ConnectAPI
from src.logger import getLogger

log = getLogger(__name__)

class TestConnect(TestCase):
    def test_connection(self):
        try:
            with ConnectAPI(
                    alias=os.environ["MILVUS_DB"],
                    uri=os.environ["MILVUS_DB_URI"],
                    user=os.environ["MILVUS_USER"],
                    password=os.environ["MILVUS_PASSWORD"],
                    db_name=os.environ["MILVUS_DB"],
                    token=os.environ["MILVUS_DB_TOKEN"],
                    timeout=30
            ) as connect_api:
                log.info(f"ConnectAPI: {connect_api.to_json()}")
                databases = connect_api.client.list_databases()
                log.info(f"Databases: {databases}")
                assert os.environ["MILVUS_DB"] in databases
        except Exception as e:
            log.error(f"Connection test failed: {e}", exc_info=True)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
