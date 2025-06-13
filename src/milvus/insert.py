from typing import Any

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.interfaces import ICommand, IOperation, IStrategy, IVectorAPI

# Logging setup
log = GetLogger(__name__)


class InsertOperation(IOperation):
    """Template method for insert operations in Milvus.

    Implements the IOperation interface to define a structured insertion process with validation,
    performance, and post-processing steps.

    Attributes:
        api (VectorAPI): The vector API instance.

    Methods:
        validate: Validates the input parameters.
        perform: Performs the insertion operation.
        post_process: Handles post-processing of the result.
        execute: Executes the full operation (inherited).

    Example:
        ```python
        api = VectorAPI(connect_api)
        operation = InsertOperation(api)
        result = operation.execute("test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.

    """

    def __init__(self, api: 'VectorAPI'):
        self.api = api

    def validate(self,
                       collection_name: str,
                       entities: list[dict[str, Any]], **kwargs) -> bool:
        """Validates the input parameters for the insertion operation.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            **kwargs: Additional parameters.

        Returns:
            bool: True if validation passes, False otherwise.

        Raises:
            MilvusValidationError: If validation fails.

        """
        if not collection_name or not entities:
            raise MilvusValidationError("Invalid input")
        if not isinstance(entities, list) or not all(isinstance(e, dict) for e in entities):
            raise MilvusValidationError("Entities must be a list of dictionaries")
        if not all("vector" in e for e in entities):
            raise MilvusValidationError("Each entity must contain a 'vector' field")
        if not all(isinstance(e["vector"], list) for e in entities):
            raise MilvusValidationError("Each vector must be a list")
        if not all(isinstance(i, float) for e in entities for i in e["vector"]):
            raise MilvusValidationError("Each vector must contain float values")
        if not all(len(e["vector"]) == len(entities[0]["vector"]) for e in entities):
            raise MilvusValidationError("All vectors must have the same length")
        log.info(f"Validated {len(entities)} entities for insertion into {collection_name}")
        return True

    def perform(self,
                      collection_name: str,
                      entities: list[dict[str, Any]], **kwargs):
        """Performs the insertion operation.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            **kwargs: Additional parameters.

        Returns:
            Any: Result of the insertion operation.

        """
        return self.api.insert(collection_name, entities, **kwargs)

    def post_process(self, result):
        """Handles post-processing of the insertion result.

        Args:
            result: Result of the insertion operation.

        """
        if not result:
            raise MilvusAPIError("Insertion failed")
        # TODO: Add any additional post-processing steps if needed
        log.info(f"Inserted {len(result)} entities")


class InsertCommand(ICommand):
    """Command for inserting data into Milvus collections.

    Implements the ICommand interface to encapsulate insertion operations.

    Attributes:
        api (VectorAPI): The vector API instance.
        collection_name (str): Name of the collection.
        entities (List[Dict[str, Any]]): Entities to insert.

    Methods:
        execute: Executes the insertion command.

    Example:
        ```python
        api = VectorAPI(connect_api)
        command = InsertCommand(api, "test_collection", [{"vector": [0.1] * 128}])
        result = command.execute()
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.

    """

    def __init__(self, api: 'VectorAPI', collection_name: str, entities: list[dict[str, Any]]):
        self.api = api
        self.collection_name = collection_name
        self.entities = entities

    def execute(self):
        """Executes the insertion command.

        Returns:
            Any: Result of the insertion operation.

        """
        return self.api.insert(self.collection_name, self.entities)


class InsertStrategy(IStrategy):
    """Strategy for inserting data into Milvus collections.

    Implements the IStrategy interface to define data insertion behavior.

    Methods:
        execute: Performs the insertion operation.

    Example:
        ```python
        strategy = InsertStrategy()
        api = VectorAPI(connect_api)
        result = strategy.execute(api, "test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.

    """

    def execute(self,
                      api: IVectorAPI,
                      collection_name: str,
                      entities: list[dict[str, Any]], **kwargs):
        """Performs the insertion operation.

        Args:
            api (VectorAPI): The vector API instance.
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            **kwargs: Additional insertion parameters.

        Returns:
            Any: Result of the insertion operation.

        """
        return api.insert(collection_name, entities, **kwargs)

