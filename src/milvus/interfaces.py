#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src.interfaces.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Annotated, Union
import numpy as np
from pymilvus import AsyncMilvusClient, MilvusClient, Collection, FieldSchema
from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)

# Abstract Interfaces
class IConnectAPI(ABC):
    """
    Interface for managing connections to the Milvus server.

    This interface defines methods for connecting and disconnecting from the
    Milvus server, ensuring a standardized way to handle server interactions.

    Attributes:
        client (AsyncMilvusClient | MilvusClient): An instance of AsyncMilvusClient or
        MilvusClient used to interact with the Milvus server.

    Methods:
        connect: Establishes an asynchronous connection to the Milvus server.
        disconnect: Terminates the connection to the Milvus server asynchronously.

    Raises:
        MilvusAPIError: If connection or disconnection operations fail due to server issues.
        MilvusValidationError: If connection parameters are invalid.

    Example:
        ```python
        class MilvusConnection(IConnectAPI):
            def connect(self, alias, user, password, host, port, timeout, **kwargs):
                self.client = AsyncMilvusClient()
                self.client.connect(alias=alias, user=user, password=password, host=host, port=port, timeout=timeout)
            def disconnect(self):
                self.client.close()
        ```
    """
    client: Annotated[Union[MilvusClient],
        "An instance of AsyncMilvusClient or MilvusClient for server interaction."
    ]

    @abstractmethod
    def connect(self, alias: str, user: str, password: str, host: str, port: str, timeout: int, **kwargs):
        """
        Connects to the Milvus server asynchronously.

        Parameters:
            alias (str): Alias for the connection.
            user (str): Username for authentication.
            password (str): Password for authentication.
            host (str): Milvus server host address.
            port (str): Milvus server port.
            timeout (int): Connection timeout in seconds.
            **kwargs: Additional connection parameters.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'connect' method must be implemented by subclasses to establish a connection.")

    @abstractmethod
    def disconnect(self):
        """
        Disconnects from the Milvus server asynchronously.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'disconnect' method must be implemented by subclasses to close the connection.")


class ICollectionAPI(ABC):
    """
    Interface for managing Milvus collections.

    Provides methods for creating, listing, describing, and dropping collections in Milvus.
    Implementations must handle all collection-related operations.

    Methods:
        create_collection: Creates a new collection in the specified database.
        list_collections: Lists all collections in the specified database.
        describe_collection: Retrieves details about a specific collection.
        drop_collection: Deletes a collection from the database.

    Raises:
        MilvusAPIError: If collection operations fail due to server issues.
        MilvusValidationError: If input parameters are invalid.

    Example:
        ```python
        class MilvusCollectionAPI(ICollectionAPI):
            def create_collection(self, collection_name, fields, database_name, **kwargs):
                schema = CollectionSchema(fields=fields)
                return Collection(collection_name, schema, **kwargs)
        ```
    """
    @abstractmethod
    def create_collection(self, collection_name: str, fields: List[FieldSchema], database_name: str,
                                **kwargs) -> Collection:
        """
        Creates a new collection in the specified database.

        Parameters:
            collection_name (str): Name of the collection to create.
            fields (List[FieldSchema]): List of field schemas defining the collection structure.
            database_name (str): Name of the database where the collection will be created.
            **kwargs: Additional parameters for collection creation.

        Returns:
            Collection: The created collection object.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'create_collection' method must be implemented by subclasses to create a collection.")

    @abstractmethod
    def list_collections(self, database_name: str) -> List[str]:
        """
        Lists all collections in the specified database.

        Parameters:
            database_name (str): Name of the database to query.

        Returns:
            List[str]: List of collection names.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'list_collections' method must be implemented by subclasses to list collections.")

    @abstractmethod
    def describe_collection(self, collection_name: str, database_name: str) -> Dict[str, Any]:
        """
        Describes the specified collection.

        Parameters:
            collection_name (str): Name of the collection to describe.
            database_name (str): Name of the database containing the collection.

        Returns:
            Dict[str, Any]: Dictionary containing collection details.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'describe_collection' method must be implemented by subclasses to describe a collection.")

    @abstractmethod
    def drop_collection(self, collection_name: str, database_name: str) -> Dict[str, str]:
        """
        Drops the specified collection.

        Parameters:
            collection_name (str): Name of the collection to drop.
            database_name (str): Name of the database containing the collection.

        Returns:
            Dict[str, str]: Status of the drop operation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'drop_collection' method must be implemented by subclasses to drop a collection.")


class IVectorAPI(ABC):
    """
    Interface for vector operations in Milvus.

    Defines methods for inserting and deleting vectors in collections.

    Methods:
        insert: Inserts entities into a collection.
        delete: Deletes entities from a collection based on an expression.

    Raises:
        MilvusAPIError: If vector operations fail due to server issues.
        MilvusValidationError: If input parameters are invalid.

    Example:
        ```python
        class MilvusVectorAPI(IVectorAPI):
            def insert(self, collection_name, entities, partition_name, database_name):
                collection = Collection(collection_name)
                return collection.insert(entities)
        ```
    """
    @abstractmethod
    def insert(self, collection_name: str, entities: List[Dict[str, Any]], partition_name: Optional[str],
                     database_name: str) -> List[int]:
        """
        Inserts entities into a collection.

        Parameters:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): List of entities to insert.
            partition_name (Optional[str]): Name of the partition, if any.
            database_name (str): Name of the database.

        Returns:
            List[int]: IDs of inserted entities.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'insert' method must be implemented by subclasses to insert entities.")

    @abstractmethod
    def delete(self, collection_name: str, expr: str, partition_name: Optional[str], database_name: str):
        """
        Deletes entities from a collection based on an expression.

        Parameters:
            collection_name (str): Name of the collection.
            expr (str): Expression defining entities to delete.
            partition_name (Optional[str]): Name of the partition, if any.
            database_name (str): Name of the database.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'delete' method must be implemented by subclasses to delete entities.")


class ISearchAPI(ABC):
    """
    Interface for vector search operations in Milvus.

    Provides a method for searching vectors with optional reranking.

    Methods:
        search: Performs a vector search in the specified collection.

    Raises:
        MilvusAPIError: If search operations fail due to server issues.
        MilvusValidationError: If search parameters are invalid.

    Example:
        ```python
        class MilvusSearchAPI(ISearchAPI):
            def search(self, collection_name, data, anns_field, param, limit, expr, output_fields, partition_names, database_name, **kwargs):
                collection = Collection(collection_name)
                return collection.search(data, anns_field, param, limit, expr, output_fields, partition_names)
        ```
    """
    @abstractmethod
    def search(self, collection_name: str, data: List[List[float]], anns_field: str, param: Dict[str, Any],
                     limit: int, expr: Optional[str], output_fields: Optional[List[str]],
                     partition_names: Optional[List[str]], database_name: str, **kwargs) -> List[Dict]:
        """
        Performs a vector search in the specified collection.

        Parameters:
            collection_name (str): Name of the collection to search.
            data (List[List[float]]): Query vectors for the search.
            anns_field (str): Name of the vector field to search.
            param (Dict[str, Any]): Search parameters (e.g., metric type).
            limit (int): Maximum number of results to return.
            expr (Optional[str]): Boolean expression to filter results.
            output_fields (Optional[List[str]]): Fields to include in results.
            partition_names (Optional[List[str]]): Partitions to search.
            database_name (str): Name of the database.
            **kwargs: Additional search parameters.

        Returns:
            List[Dict]: Search results.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'search' method must be implemented by subclasses to perform vector search.")


class IIndexAPI(ABC):
    """
    Interface for managing indexes in Milvus collections.

    Defines methods for creating and dropping indexes on fields.

    Methods:
        create_index: Creates an index on a field in a collection.
        drop_index: Drops an index from a field in a collection.

    Raises:
        MilvusAPIError: If index operations fail due to server issues.
        MilvusValidationError: If index parameters are invalid.

    Example:
        ```python
        class MilvusIndexAPI(IIndexAPI):
            def create_index(self, collection_name, field_name, index_params, database_name, **kwargs):
                collection = Collection(collection_name)
                collection.create_index(field_name, index_params)
        ```
    """
    @abstractmethod
    def create_index(self, collection_name: str, field_name: str, index_params: Dict, database_name: str,
                           **kwargs):
        """
        Creates an index on a field in a collection.

        Parameters:
            collection_name (str): Name of the collection.
            field_name (str): Name of the field to index.
            index_params (Dict): Parameters for the index (e.g., index type).
            database_name (str): Name of the database.
            **kwargs: Additional index parameters.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'create_index' method must be implemented by subclasses to create an index.")

    @abstractmethod
    def drop_index(self, collection_name: str, field_name: str, database_name: str):
        """
        Drops an index from a field in a collection.

        Parameters:
            collection_name (str): Name of the collection.
            field_name (str): Name of the field with the index.
            database_name (str): Name of the database.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'drop_index' method must be implemented by subclasses to drop an index.")


class IPartitionAPI(ABC):
    """
    Interface for managing partitions in Milvus collections.

    Provides methods for creating and dropping partitions.

    Methods:
        create_partition: Creates a partition in a collection.
        drop_partition: Drops a partition from a collection.

    Raises:
        MilvusAPIError: If partition operations fail due to server issues.
        MilvusValidationError: If partition parameters are invalid.

    Example:
        ```python
        class MilvusPartitionAPI(IPartitionAPI):
            def create_partition(self, collection_name, partition_name, database_name):
                collection = Collection(collection_name)
                collection.create_partition(partition_name)
        ```
    """
    @abstractmethod
    def create_partition(self, collection_name: str, partition_name: str, database_name: str):
        """
        Creates a partition in a collection.

        Parameters:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition to create.
            database_name (str): Name of the database.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'create_partition' method must be implemented by subclasses to create a partition.")

    @abstractmethod
    def drop_partition(self, collection_name: str, partition_name: str, database_name: str):
        """
        Drops a partition from a collection.

        Parameters:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition to drop.
            database_name (str): Name of the database.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'drop_partition' method must be implemented by subclasses to drop a partition.")


class IStatAPI(ABC):
    """
    Interface for retrieving collection statistics in Milvus.

    Defines a method to get statistical information about a collection.

    Methods:
        get_collection_stats: Retrieves statistics for a collection.

    Raises:
        MilvusAPIError: If statistics retrieval fails due to server issues.
        MilvusValidationError: If input parameters are invalid.

    Example:
        ```python
        class MilvusStatAPI(IStatAPI):
            def get_collection_stats(self, collection_name, database_name):
                collection = Collection(collection_name)
                return collection.stats()
        ```
    """
    @abstractmethod
    def get_collection_stats(self, collection_name: str, database_name: str) -> Dict[str, Any]:
        """
        Gets statistics for a collection.

        Parameters:
            collection_name (str): Name of the collection.
            database_name (str): Name of the database.

        Returns:
            Dict[str, Any]: Collection statistics.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'get_collection_stats' method must be implemented by subclasses to retrieve statistics.")


class IMonitorAPI(ABC):
    """
    Interface for monitoring the Milvus server.

    Provides a method to retrieve monitoring information.

    Methods:
        get_monitor_info: Retrieves monitoring information for the Milvus server.

    Raises:
        MilvusAPIError: If monitoring operations fail due to server issues.

    Example:
        ```python
        class MilvusMonitorAPI(IMonitorAPI):
            def get_monitor_info(self):
                return {"status": "healthy", "uptime": "24h"}
        ```
    """
    @abstractmethod
    def get_monitor_info(self) -> Dict[str, Any]:
        """
        Gets monitoring information for the Milvus server.

        Returns:
            Dict[str, Any]: Monitoring information.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'get_monitor_info' method must be implemented by subclasses to retrieve monitoring info.")


class IEmbeddingAPI(ABC):
    """
    Interface for generating embeddings in Milvus.

    Defines a method to generate embeddings using a provided model.

    Methods:
        generate_embeddings: Generates embeddings for the provided data.

    Raises:
        MilvusValidationError: If input data or model parameters are invalid.

    Example:
        ```python
        class MilvusEmbeddingAPI(IEmbeddingAPI):
            def generate_embeddings(self, data, embedding_model, embedding_type, batch_size):
                return embedding_model(data)
        ```
    """
    @abstractmethod
    def generate_embeddings(self, data: List[Any], embedding_model: Callable[[List[Any]], np.ndarray],
                                  embedding_type: str, batch_size: int) -> np.ndarray:
        """
        Generates embeddings for the provided data.

        Parameters:
            data (List[Any]): Input data to generate embeddings for.
            embedding_model (Callable[[List[Any]], np.ndarray]): Model to generate embeddings.
            embedding_type (str): Type of embeddings (e.g., "text", "image").
            batch_size (int): Size of data batches for processing.

        Returns:
            np.ndarray: Generated embeddings.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'generate_embeddings' method must be implemented by subclasses to generate embeddings.")


class IAdminAPI(ABC):
    """
    Interface for administrative tasks in Milvus.

    Provides methods for managing users and other administrative functions.

    Methods:
        create_user: Creates a new user in Milvus.
        list_users: Lists all users in Milvus.

    Raises:
        MilvusAPIError: If administrative operations fail due to server issues.
        MilvusValidationError: If user parameters are invalid.

    Example:
        ```python
        class MilvusAdminAPI(IAdminAPI):
            def create_user(self, username, password):
                # Implementation to create user
                pass
        ```
    """
    @abstractmethod
    def create_user(self, username: str, password: str):
        """
        Creates a new user in Milvus.

        Parameters:
            username (str): Username for the new user.
            password (str): Password for the new user.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'create_user' method must be implemented by subclasses to create a user.")

    @abstractmethod
    def list_users(self) -> List[str]:
        """
        Lists all users in Milvus.

        Returns:
            List[str]: List of usernames.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'list_users' method must be implemented by subclasses to list users.")


class IDataImportAPI(ABC):
    """
    Interface for importing data into Milvus collections.

    Defines a method to import data from files.

    Methods:
        import_data: Imports data into a collection from a file.

    Raises:
        MilvusAPIError: If data import fails due to server issues.
        MilvusValidationError: If file path or data format is invalid.

    Example:
        ```python
        class MilvusDataImportAPI(IDataImportAPI):
            def import_data(self, collection_name, file_path, database_name):
                # Implementation to import data
                pass
        ```
    """
    @abstractmethod
    def import_data(self, collection_name: str, file_path: str, database_name: str):
        """
        Imports data into a collection from a file.

        Parameters:
            collection_name (str): Name of the collection.
            file_path (str): Path to the data file.
            database_name (str): Name of the database.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'import_data' method must be implemented by subclasses to import data.")


class IStrategy(ABC):
    """
    Abstract base class for strategies.

    Defines a method for executing a strategy.

    Methods:
        execute: Executes the strategy with provided arguments.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteStrategy(IStrategy):
            def execute(self, *args, **kwargs):
                # Strategy implementation
                pass
        ```
    """
    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Executes the strategy.

        Parameters:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'execute' method must be implemented by subclasses to execute the strategy.")


class ICommand(ABC):
    """
    Abstract base class for commands.

    Defines a method for executing a command.

    Methods:
        execute: Executes the command.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteCommand(ICommand):
            def execute(self):
                # Command implementation
                pass
        ```
    """
    @abstractmethod
    def execute(self):
        """
        Executes the command.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'execute' method must be implemented by subclasses to execute the command.")


class IOperation(ABC):
    """
    Template Method pattern for operations.

    Defines a template for executing operations with validation, performance, and post-processing steps.

    Methods:
        execute: Executes the operation with validation, performance, and post-processing.
        validate: Validates the operation parameters.
        perform: Performs the main operation logic.
        post_process: Handles post-processing of the operation result.

    Raises:
        NotImplementedError: If abstract methods are not implemented by a subclass.

    Example:
        ```python
        class ConcreteOperation(IOperation):
            def validate(self, *args, **kwargs):
                # Validation logic
                pass
            def perform(self, *args, **kwargs):
                # Operation logic
                pass
            def post_process(self, result):
                # Post-processing logic
                pass
        ```
    """
    def execute(self, *args, **kwargs):
        """
        Executes the operation with validation, performance, and post-processing.

        Parameters:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Returns:
            Any: Result of the operation.
        """
        self.validate(*args, **kwargs)
        result = self.perform(*args, **kwargs)
        self.post_process(result)
        return result

    @abstractmethod
    def validate(self, *args, **kwargs):
        """
        Validates the operation parameters.

        Parameters:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'validate' method must be implemented by subclasses to validate operation parameters.")

    @abstractmethod
    def perform(self, *args, **kwargs):
        """
        Performs the main operation logic.

        Parameters:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Returns:
            Any: Result of the operation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'perform' method must be implemented by subclasses to perform the operation.")

    @abstractmethod
    def post_process(self, result):
        """
        Handles post-processing of the operation result.

        Parameters:
            result: Result of the operation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'post_process' method must be implemented by subclasses to handle post-processing.")


class ICollectionVisitor(ABC):
    """
    Visitor for collection operations.

    Defines a method for visiting a collection to perform operations.

    Methods:
        visit_collection: Performs an operation on a collection.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteVisitor(ICollectionVisitor):
            def visit_collection(self, collection):
                # Visitor logic
                pass
        ```
    """
    @abstractmethod
    def visit_collection(self, collection):
        """
        Performs an operation on a collection.

        Parameters:
            collection: The collection to visit.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'visit_collection' method must be implemented by subclasses to visit a collection.")


class IState(ABC):
    """
    Abstract base class for state pattern.

    Defines a method for handling state-specific behavior.

    Methods:
        handle: Handles the state-specific behavior.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteState(IState):
            def handle(self, context):
                # State handling logic
                pass
        ```
    """
    @abstractmethod
    def handle(self, context):
        """
        Handles the state-specific behavior.

        Parameters:
            context: The context in which the state operates.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'handle' method must be implemented by subclasses to handle state behavior.")


class IHandler(ABC):
    """
    Abstract base class for chain of responsibility.

    Defines methods for handling requests in a chain of responsibility pattern.

    Attributes:
        next_handler (IHandler): The next handler in the chain.

    Methods:
        set_next: Sets the next handler in the chain.
        handle: Handles the request or passes it to the next handler.

    Raises:
        NotImplementedError: If the handle method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteHandler(IHandler):
            def handle(self, request):
                # Handle request or pass to next
                pass
        ```
    """
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler):
        """
        Sets the next handler in the chain.

        Parameters:
            handler (IHandler): The next handler.

        Returns:
            IHandler: The next handler for method chaining.
        """
        self.next_handler = handler
        return handler

    @abstractmethod
    def handle(self, request):
        """
        Handles the request or passes it to the next handler.

        Parameters:
            request: The request to handle.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'handle' method must be implemented by subclasses to handle requests.")


class IBridgeImplementor(ABC):
    """
    Bridge implementor for abstraction separation.

    Defines a method for implementing operations separately from the abstraction.

    Methods:
        operation: Performs the implementation-specific operation.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteImplementor(IBridgeImplementor):
            def operation(self):
                # Implementation logic
                pass
        ```
    """
    @abstractmethod
    def operation(self):
        """
        Performs the implementation-specific operation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'operation' method must be implemented by subclasses to perform the operation.")


class ICollectionObserver(ABC):
    """
    Observer for collection changes.

    Defines a method for updating based on collection events.

    Methods:
        update: Updates the observer based on a collection event.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteObserver(ICollectionObserver):
            def update(self, event):
                # Observer logic
                pass
        ```
    """
    @abstractmethod
    def update(self, event):
        """
        Updates the observer based on a collection event.

        Parameters:
            event: The event triggering the update.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'update' method must be implemented by subclasses to handle collection updates.")


class IConnectionManager(ABC):
    """
    Interface for managing connections to the Milvus server.

    Provides methods for establishing and closing connections.

    Methods:
        connect: Establishes a connection to the Milvus server.
        close: Closes the connection to the Milvus server.

    Raises:
        NotImplementedError: If the method is not implemented by a subclass.

    Example:
        ```python
        class ConcreteConnectionManager(IConnectionManager):
            def connect(self, alias, user, password, host, port, timeout):
                # Connection logic
                pass
        ```
    """
    @abstractmethod
    def connect(self, alias: str, user: str, password: str, host: str, port: str, timeout: int):
        """
        Establishes a connection to the Milvus server.

        Parameters:
            alias (str): Alias for the connection.
            user (str): Username for authentication.
            password (str): Password for authentication.
            host (str): Milvus server host address.
            port (str): Milvus server port.
            timeout (int): Connection timeout in seconds.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'connect' method must be implemented by subclasses to establish a connection.")

    @abstractmethod
    def close(self):
        """
        Closes the connection to the Milvus server.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("The 'close' method must be implemented by subclasses to close the connection.")



