import asyncio
import os

import numpy as np
from typing import List, Dict, Any
from pymilvus import FieldSchema, DataType, Collection, model
from src.milvus.milvus import MilvusAPI
from src.milvus.connect import ConnectAPI
from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)


# Placeholder: Simulating 10 words with random 50-dim embeddings
def placeholder_embedding_model(data: List[str]) -> np.ndarray:
    """Placeholder embedding model returning random 50-dim vectors."""
    return np.random.random((len(data), 50)).astype(np.float32)


async def main():
    """
    Implements the Attu quickstart tutorial using the provided MilvusAPI implementation.
    Steps:
    1. Connect to Milvus server
    2. Create a collection
    3. Insert data with placeholder embeddings
    4. Create an index on the vector field
    5. Perform a vector search
    6. Clean up by dropping the collection
    """
    # Step 1: Connect to Milvus server
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
            log.info(f"Connected to Milvus successfully with {connect_api}")
            log.info(f"Connecting to Milvus with alias: {connect_api._alias}")
            log.info(f"Connection parameters: {connect_api.__dict__}")
            log.info(f"Connecting to Milvus at {connect_api._host}:{connect_api._port}")

    except Exception as e:
        log.error(f"Failed to connect to Milvus: {e}")
        return

    # Initialize MilvusAPI
    api = MilvusAPI(connect_api)

    # Step 2: Create a collection
    collection_name = "word_collection"
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="word", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=50)  # Using 50-dim as per tutorial
    ]
    try:
        # Step 2.1: Initialize SentenceTransformerEmbeddingFunction
        sentence_transformer_ef = model.dense.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2',  # Specify the model name
            device='cpu'  # Specify the device to use, e.g., 'cpu' or 'cuda:0'
        )

        # Step 3: Insert data with placeholder embeddings
        words = ["apple", "banana", "car", "dog", "elephant", "flower", "guitar", "house", "island", "jungle"]
        entities = [{"word": word, "vector": sentence_transformer_ef.encode_documents([word])[0].tolist()} for word in
                    words]
        dimensions = entities
        log.info(f"Creating collection: {collection_name}")
        collection = await api.create_collection(
            collection_name=collection_name,
            fields=fields,
            database_name=os.environ["MILVUS_DB"],
            dimension=50,
            metric_type="L2",  # Tutorial uses L2 distance
            auto_id=True
        )
        log.info(f"Collection {collection.name} created successfully")
    except Exception as e:
        log.error(f"Failed to create collection: {e}")
        connect_api.disconnect()
        return


    try:
        log.info(f"Inserting {len(entities)} entities into {collection_name}")
        result = await api.insert(
            collection_name=collection_name,
            entities=entities,
            database_name=os.environ["MILVUS_DB"]
        )
        log.info(f"Inserted {len(entities)} entities: {result}")
    except Exception as e:
        log.error(f"Failed to insert entities: {e}")
        await api.drop_collection(collection_name)
        connect_api.disconnect()
        return

    # Step 4: Create an index on the vector field
    index_params = {
        "index_type": "IVF_FLAT",  # Tutorial uses IVF_FLAT
        "metric_type": "L2",
        "params": {"nlist": 128}
    }
    try:
        log.info(f"Creating index on vector field in {collection_name}")
        api.create_index(
            collection_name=collection_name,
            field_name="vector",
            index_params=index_params,
            database_name=os.environ["MILVUS_DB"]
        )
        log.info(f"Index created successfully")
    except Exception as e:
        log.error(f"Failed to create index: {e}")
        await api.drop_collection(collection_name)
        connect_api.disconnect()
        return

    # Step 5: Perform a vector search
    query_vector = placeholder_embedding_model(["apple"])[0].tolist()  # Search for "apple" vector
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    try:
        log.info(f"Performing vector search in {collection_name}")
        results = await api.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params=search_params,
            limit=5,
            output_fields=["word"],
            database_name=os.environ["MILVUS_DB"]
        )
        log.info(f"Search results: {results}")
        for result in results:
            log.info(f"ID: {result['id']}, Word: {result['word']}, Distance: {result['distance']}")
    except Exception as e:
        log.error(f"Failed to perform search: {e}")
        await api.drop_collection(collection_name)
        connect_api.disconnect()
        return

    # Step 6: Clean up
    try:
        log.info(f"Dropping collection: {collection_name}")
        await api.drop_collection(collection_name)
        log.info(f"Collection {collection_name} dropped successfully")
    except Exception as e:
        log.error(f"Failed to drop collection: {e}")
    finally:
        connect_api.disconnect()


if __name__ == "__main__":
    asyncio.run(main())