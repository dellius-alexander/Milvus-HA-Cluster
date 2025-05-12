#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src.milvus.py
"""
Milvus API Implementation

This module provides a robust, extensible, and maintainable interface to the Milvus vector database using Python.
It integrates core functionality for managing collections, vectors, indexes, and embeddings, with support for
asynchronous operations, configuration management, security, and error handling. The implementation employs
several design patterns (Singleton, Factory, Builder, Strategy, Command, Template Method, Facade) to ensure
flexibility and reusability.

Key Features:
- Asynchronous Milvus operations (create, insert, search, delete, etc.)
- Support for multiple embedding types and models
- Configuration management via JSON or environment variables
- Basic security with encryption and authentication
- Comprehensive logging and error handling with retries
- Design patterns for extensibility and maintainability

Example Usage:
=============

```python

import asyncio
from milvus_api import MilvusAPI
>>>
async def main():
   async with ConnectAPI(
           alias="test_db",
           user="root",
           password="Milvus",
           host="10.1.0.99",
           port="19530",
           timeout=10,
           **{"db_name": "test_db"}
       ) as connect_api:
   api = MilvusAPI()
    # Create a collection
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
    ]
    await api.create_collection("test_collection", fields, "test_db")
    # Insert data
    entities = [{"vector": [0.1] * 128} for _ in range(10)]
    await api.insert("test_collection", entities, timeout="test_db")
    # Search
    results = await api.search("test_collection", [[0.1] * 128], "vector", {"metric_type": "COSINE"}, 5)
    print(f"Search results: {results}")
    # Clean up
    await api.drop_collection("test_collection", "test_db")

asyncio.run(main())

```
"""
import asyncio
import base64
import os
from dataclasses import dataclass
from inspect import Traceback
from typing import List, Dict, Any, Optional, Callable, Coroutine, Annotated, Union

import dotenv
import numpy as np
from pygments.lexer import using
from pymilvus import (
    FieldSchema, Collection, DataType, MilvusException, utility,
    CollectionSchema, AsyncMilvusClient, MilvusClient,
)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import datetime
import traceback
import sys
from src.exceptions import MilvusAPIError, MilvusValidationError
from src.interfaces import IConnectAPI, ICollectionAPI, IVectorAPI, ISearchAPI, IIndexAPI, IPartitionAPI, IStatAPI, \
    IEmbeddingAPI, IMonitorAPI, IAdminAPI, IDataImportAPI, IStrategy, ICommand, IOperation, IState
from src.utils import async_log_decorator, SecurityManager, ConfigManager
from src.logger import getLogger as GetLogger


# Logging setup
log = GetLogger(__name__)


# Design Patterns
class SingletonMeta(type):
    """
    Metaclass for implementing the Singleton pattern.

    Ensures that only one instance of a class is created.

    Attributes:
        _instances (Dict): Dictionary storing class instances.

    Methods:
        __call__: Creates or returns the singleton instance.

    Example:
        ```python
        class MyClass(metaclass=SingletonMeta):
            pass
        instance1 = MyClass()
        instance2 = MyClass()
        assert instance1 is instance2
        ```

    Raises:
        NotImplementedError: If the __call__ method is not implemented correctly.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Creates or returns the singleton instance.

        Args:
            cls (type): The class being instantiated.
            *args: Positional arguments for class initialization.
            **kwargs: Keyword arguments for class initialization.

        Returns:
            object: The singleton instance of the class.

        Raises:
            NotImplementedError: If the method is not implemented correctly.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class CollectionFactory:
    """
    Factory for creating collections with predefined configurations.

    Provides methods to create standard collections with common fields.

    Methods:
        create_standard_collection: Creates a collection with ID and vector fields.

    Example:
        ```python
        factory = CollectionFactory()
        collection = await factory.create_standard_collection("test_collection", 128, "test_db")
        ```

    Raises:
        MilvusValidationError: If input parameters are invalid.
        MilvusAPIError: If collection creation fails.
    """

    @staticmethod
    async def create_standard_collection(collection_name: str, dimension: int, db_name: str) -> Collection:
        """
         Creates a standard collection with ID and vector fields.

         Args:
             collection_name (str): Name of the collection.
             dimension (int): Dimension of the vector field.
             db_name (str): Name of the database.

         Returns:
             Collection: The created collection object.

         Raises:
             NotImplementedError: If the method is not implemented by a subclass.
         """
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension)
        ]
        return await CollectionAPI(ConnectAPI()).create_collection(collection_name, fields, db_name)


class CollectionSchemaBuilder:
    """
    Builder for constructing CollectionSchema objects.

    Allows incremental construction of collection schemas with fields and descriptions.

    Attributes:
        _fields (List[FieldSchema]): List of field schemas.
        _description (str): Description of the collection schema.

    Methods:
        add_field: Adds a field to the schema.
        set_description: Sets the schema description.
        build: Constructs the final CollectionSchema.

    Example:
        ```python
        builder = CollectionSchemaBuilder()
        builder.add_field("id", DataType.INT64, is_primary=True)
        builder.add_field("vector", DataType.FLOAT_VECTOR, dim=128)
        schema = builder.build()
        ```

    Raises:
        MilvusValidationError: If the schema is invalid (e.g., no fields).
    """

    def __init__(self):
        self._fields = []
        self._description = ""

    def add_field(self, name: str, dtype: DataType, **kwargs):
        """
        Adds a field to the schema.

        Args:
            name (str): Name of the field.
            dtype (DataType): Data type of the field.
            **kwargs: Additional field parameters.

        Returns:
            CollectionSchemaBuilder: Self for method chaining.
        """
        self._fields.append(FieldSchema(name=name, dtype=dtype, **kwargs))
        return self

    def set_description(self, description: str):
        """
        Sets the schema description.

        Args:
            description (str): Description of the schema.

        Returns:
            CollectionSchemaBuilder: Self for method chaining.
        """
        self._description = description
        return self

    def build(self) -> CollectionSchema:
        """
        Constructs the final CollectionSchema.

        Returns:
            CollectionSchema: The constructed schema.
        """
        if not self._fields:
            raise MilvusValidationError("Schema must have at least one field")
        return CollectionSchema(fields=self._fields, description=self._description)


class InsertStrategy(IStrategy):
    """
    Strategy for inserting data into Milvus collections.

    Implements the IStrategy interface to define data insertion behavior.

    Methods:
        execute: Performs the insertion operation.

    Example:
        ```python
        strategy = InsertStrategy()
        api = VectorAPI(connect_api)
        result = await strategy.execute(api, "test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.
    """

    async def execute(self,
                      api: IVectorAPI,
                      collection_name: str,
                      entities: List[Dict[str, Any]], **kwargs):
        """
        Performs the insertion operation.

        Args:
            api (VectorAPI): The vector API instance.
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            **kwargs: Additional insertion parameters.

        Returns:
            Any: Result of the insertion operation.
        """
        return await api.insert(collection_name, entities, **kwargs)


class SearchStrategy(IStrategy):
    """
    Strategy for searching data in Milvus collections.

    Implements the IStrategy interface to define search behavior.

    Methods:
        execute: Performs the search operation.

    Example:
        ```python
        strategy = SearchStrategy()
        api = SearchAPI(connect_api)
        result = await strategy.execute(api, "test_collection", [[0.1] * 128], "vector", 5)
        ```

    Raises:
        MilvusAPIError: If the search operation fails.
        MilvusValidationError: If input parameters are invalid.
    """
    async def execute(self,
                      api: ISearchAPI,
                      collection_name: str,
                      data: List[List[float]],
                      anns_field: str,
                      limit: int, **kwargs):
        """
        Performs the search operation.

        Args:
            api (ISearchAPI): The search API instance.
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            limit (int): Maximum number of results.
            **kwargs: Additional search parameters.

        Returns:
            Any: Result of the search operation.
       """
        return await api.search(collection_name, data, anns_field, {"metric_type": "COSINE"}, limit, **kwargs)


class InsertCommand(ICommand):
    """
    Command for inserting data into Milvus collections.

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
        result = await command.execute()
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.
    """
    def __init__(self, api: 'VectorAPI', collection_name: str, entities: List[Dict[str, Any]]):
        self.api = api
        self.collection_name = collection_name
        self.entities = entities

    async def execute(self):
        """
        Executes the insertion command.

        Returns:
            Any: Result of the insertion operation.
        """
        return await self.api.insert(self.collection_name, self.entities)


class InsertOperation(IOperation):
    """
    Template method for insert operations in Milvus.

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
        result = await operation.execute("test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If the insertion operation fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, api: 'VectorAPI'):
        self.api = api

    async def validate(self,
                       collection_name: str,
                       entities: List[Dict[str, Any]], **kwargs) -> bool:
        """
        Validates the input parameters for the insertion operation.

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

    async def perform(self,
                      collection_name: str,
                      entities: List[Dict[str, Any]], **kwargs):
        """
        Performs the insertion operation.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            **kwargs: Additional parameters.

        Returns:
            Any: Result of the insertion operation.
        """
        return await self.api.insert(collection_name, entities, **kwargs)

    async def post_process(self, result):
        """
        Handles post-processing of the insertion result.

        Args:
            result: Result of the insertion operation.

        """
        if not result:
            raise MilvusAPIError("Insertion failed")
        # TODO: Add any additional post-processing steps if needed
        log.info(f"Inserted {len(result)} entities")



class CollectionPrototype:
    """
    Prototype for cloning collections.

    Allows creating copies of collections for reuse or modification.

    Attributes:
        collection (Collection): The collection to clone.

    Methods:
        clone: Creates a deep copy of the collection.

    Example:
        ```python
        collection = Collection("test_collection")
        prototype = CollectionPrototype(collection)
        cloned_collection = prototype.clone()
        ```

    Raises:
        MilvusAPIError: If cloning fails.
    """

    def __init__(self, collection: Collection):
        self.collection = collection

    def clone(self):
        """
        Creates a deep copy of the collection.

        Returns:
            Collection: A deep copy of the collection.
        """
        from copy import deepcopy
        return deepcopy(self.collection)


class CollectionComposite:
    """
    Composite for managing complex collections.

    Allows hierarchical organization of collection components.

    Attributes:
        name (str): Name of the composite.
        children (List): List of child components.

    Methods:
        add: Adds a component to the composite.
        remove: Removes a component from the composite.

    Example:
        ```python
        composite = CollectionComposite("parent_collection")
        composite.add(CollectionComposite("child_collection"))
        ```

    Raises:
        MilvusValidationError: If invalid components are added or removed.
    """

    def __init__(self, name: str):
        self.name = name
        self.children = []

    def add(self, component):
        """
        Adds a component to the composite.

        Args:
            component: The component to add.
        """
        self.children.append(component)

    def remove(self, component):
        """
        Removes a component from the composite.

        Args:
            component: The component to remove.
        """
        self.children.remove(component)


class LoadedState(IState):
    """
    State for loaded collections.

    Implements the IState interface to handle behavior for loaded collections.

    Methods:
        handle: Handles the loaded state behavior.

    Example:
        ```python
        state = LoadedState()
        await state.handle(context)
        ```

    Raises:
        MilvusAPIError: If state handling fails.
    """

    async def handle(self, context):
        """
        Handles the loaded state behavior.

        Args:
            context: The context in which the state operates.
        """
        log.info("Collection is loaded")


class Mediator:
    """
    Mediator for collection communication.

    Facilitates communication between collections to reduce direct dependencies.

    Methods:
        notify: Notifies the mediator of an event.

    Example:
        ```python
        mediator = Mediator()
        mediator.notify("collection1", "update")
        ```

    Raises:
        MilvusAPIError: If notification handling fails.
    """

    def notify(self, sender, event):
        """
        Notifies the mediator of an event.

        Args:
            sender: The sender of the event.
            event: The event details.
        """
        log.info(f"Mediator notified by {sender} of {event}")

class Proxy:
    """
    Proxy for controlling access to Milvus operations.

    Implements access control using a security manager.

    Attributes:
        real_subject: The real subject being proxied.
        security (SecurityManager): The security manager for authorization.

    Methods:
        request: Handles the proxied request with authorization.

    Example:
        ```python
        security = SecurityManager()
        proxy = Proxy(real_subject, security)
        await proxy.request()
        ```

    Raises:
        MilvusAPIError: If authorization or request fails.
    """

    def __init__(self, real_subject, security: SecurityManager):
        self.real_subject = real_subject
        self.security = security

    async def request(self, *args, **kwargs):
        """
        Handles the proxied request with authorization.

        Args:
            *args: Positional arguments for the request.
            **kwargs: Keyword arguments for the request.

        Returns:
            Any: Result of the request.

        Raises:
            NotImplementedError: If the method is not implemented correctly.
        """
        if self.security.authorize(self.security.config.get("user"), "read"):
            return await self.real_subject.request(*args, **kwargs)
        raise MilvusAPIError("Unauthorized")


class FlyweightFactory:
    """
    Flyweight for sharing common data.

    Manages shared objects to reduce memory usage.

    Attributes:
        _flyweights (Dict): Dictionary of shared flyweight objects.

    Methods:
        get_flyweight: Retrieves or creates a flyweight object.

    Example:
        ```python
        factory = FlyweightFactory()
        flyweight = factory.get_flyweight("key")
        ```

    Raises:
        MilvusAPIError: If flyweight creation fails.
    """

    _flyweights = {}
    @classmethod
    def get_flyweight(cls, key):
        """
        Retrieves or creates a flyweight object.

        Args:
            key: The key identifying the flyweight.

        Returns:
            object: The flyweight object.
        """
        if key not in cls._flyweights:
            cls._flyweights[key] = object()
        return cls._flyweights[key]


class QueryInterpreter:
    """
    Interpreter for parsing complex queries.

    Converts query expressions into executable formats.

    Methods:
        interpret: Interprets a query expression.

    Example:
        ```python
        interpreter = QueryInterpreter()
        result = interpreter.interpret("id > 100")
        ```

    Raises:
        MilvusValidationError: If the query expression is invalid.
    """
    def interpret(self, expression: str) -> Dict:
        """
        Interprets a query expression.

        Args:
            expression (str): The query expression to interpret.

        Returns:
            Dict: The interpreted query.
        """
        return {"expr": expression}


class Memento:
    """
    Memento for saving state.

    Stores the state of an object for later restoration.

    Attributes:
        state: The state to store.

    Example:
        ```python
        memento = Memento({"key": "value"})
        ```

    Raises:
        MilvusValidationError: If the state is invalid.
    """

    def __init__(self, state):
        self.state = state


# Implementation Classes
@dataclass
class ConnectAPI(IConnectAPI):
    """
    Manages connections to the Milvus server using asynchronous operations.

    Implements the IConnectAPI interface to handle connection establishment and disconnection.
    Uses the Singleton pattern to ensure a single connection instance.

    Attributes:
        _instance (ConnectAPI): Singleton instance of ConnectAPI.
        _initialized (bool): Indicates if the connection is initialized.
        _alias (str): Connection alias.
        _timeout (int): Connection timeout in seconds.
        _user (str): Username for authentication.
        _password (str): Password for authentication.
        _host (str): Milvus server hostname.
        _port (str): Milvus server port.
        _kwargs (Dict): Additional connection parameters.
        async_client (AsyncMilvusClient | MilvusClient): The Milvus client instance.

    Methods:
        connect: Establishes a connection to the Milvus server.
        disconnect: Disconnects from the Milvus server.
        __aenter__: Enters the async context.
        __aexit__: Exits the async context.
        __await__: Makes the class awaitable.

    Example:
        ```python
        async with ConnectAPI(host="localhost", port="19530") as connect_api:
            # Perform operations
            pass
        ```

    Raises:
        MilvusAPIError: If connection or disconnection fails.
        MilvusValidationError: If connection parameters are invalid.
    """
    _instance = None
    _creation_timestamp = None
    _alias = None
    _timeout = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures a singleton instance of ConnectAPI.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            ConnectAPI: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._creation_timestamp = datetime.datetime.now()
            log.info(f"New ConnectAPI instance created @ {cls._creation_timestamp}")
        else:
            log.info(f"Using existing ConnectAPI instance created @ {cls._creation_timestamp}")
        return cls._instance

    def __init__(self, alias: str = "default", user: str = "milvus", password: str = "developer",
                 host: str = "127.0.0.1", port: str = "19530", timeout: int = 30, **kwargs):
        """Initializes ConnectAPI with connection parameters.

        Args:
            alias (str): Connection alias. Defaults to "default".
            user (str): Username for authentication. Defaults to "milvus".
            password (str): Password for authentication. Defaults to "developer".
            host (str): Milvus server hostname. Defaults to "127.0.0.1".
            port (str): Milvus server port. Defaults to "19530".
            timeout (int): Connection timeout in seconds. Defaults to 30.
            **kwargs: Additional arguments for the Milvus client.
        """
        if not hasattr(self, '_initialized') or not self._initialized:
            self._alias = alias
            self._timeout = timeout
            self._user = user
            self._password = password
            self._host = host
            self._port = port
            self._kwargs = kwargs
            self._initialized = False
        else:
            log.warning("ConnectAPI instance already exists. Using existing parameters.")

    @async_log_decorator
    async def connect(self, alias: str = "default",
                      user: str = "milvus",
                      password: str = "developer",
                      host: str = "127.0.0.1",
                      port: str = "19530",
                      timeout: int = 30, **kwargs):
        """Establishes a connection to the Milvus server.

        Args:
            alias (str): Connection alias. Defaults to "default".
            user (str): Username for authentication. Defaults to "milvus".
            password (str): Password for authentication. Defaults to "developer".
            host (str): Milvus server hostname. Defaults to "127.0.0.1".
            port (str): Milvus server port. Defaults to "19530".
            timeout (int): Connection timeout in seconds. Defaults to 30.
            **kwargs: Additional arguments for the Milvus client.

        Raises:
            MilvusAPIError: If connection fails after retries.
        """
        if not self._initialized:
            self._alias = alias
            self._timeout = timeout
            await self._connect(alias, user, password, host, port, **kwargs)
            self._initialized = True
            log.info(f"Connected to Milvus at {host}:{port} with alias {alias}")
        else:
            log.warning("Connection already initialized. Skipping reconnection.")

    @async_log_decorator
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10),
           retry=retry_if_exception_type(MilvusException))
    async def _connect(self, alias: str, user: str, password: str, host: str, port: str, **kwargs):
        """Internal method to connect with retry logic.
        This method is decorated with retry logic to handle connection failures.
        It will attempt to connect up to 3 times with exponential backoff.
        If the connection fails after 3 attempts, a MilvusAPIError is raised.
        This method is called by the connect method.

        It attempts to establish a connection to the Milvus server using the provided parameters,
        and create an AsyncMilvusClient instance.

        Args:
            alias (str): Connection alias. Defaults to "default".
            user (str): Username for authentication. Defaults to "milvus".
            password (str): Password for authentication. Defaults to "developer".
            host (str): Milvus server hostname. Defaults to "127.0.0.1".
            port (str): Milvus server port. Defaults to "19530".
            **kwargs: Additional arguments for the Milvus client.

        Raises:
            MilvusAPIError: If connection fails after retries.
        """
        try:
            # Updated kwargs to include timeout
            kwargs["timeout"] = self._timeout
            # Create a new connection
            utility.connections.connect(
                alias=alias,
                user=user,
                password=password,
                host=host,
                port=port,
                _async=True,
                **kwargs
            )

            # Create an async Milvus client
            self.async_client =  AsyncMilvusClient(
                uri=f"tcp://{host}:{port}",
                token=f"{user}:{password}",
                # db_name=alias,
                **kwargs
            )

            # Create the database
            # await self.client.create_database(alias, properties={"database.replia.number": 1})
            log.debug(f"Connected to Milvus at {host}:{port}, using: {self.async_client._using}")
        except MilvusException as e:
            log.error(f"Failed to connect: {e}")
            raise MilvusAPIError(f"Connection failed: {e}")

    @async_log_decorator
    async def disconnect(self):
        """Disconnects from the Milvus server.

        Raises:
            MilvusAPIError: If disconnection fails.
        """
        try:
            if self.async_client is not None:
                await self.async_client.close()
                log.info(f"Disconnected from Milvus, alias: {self._alias}")
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")

    @async_log_decorator
    async def __aenter__(self):
        """Enters the async context, establishing the connection."""
        if not self._initialized:
            await self.connect(
                alias=self._alias,
                user=self._user,
                password=self._password,
                host=self._host,
                port=self._port,
                timeout=self._timeout,
                **self._kwargs
            )
        return self

    @async_log_decorator
    async def __aexit__(self, exc_type: Exception = None, exc_val: Any = None, exc_tb: Traceback = None):
        """
        Exits the async context, disconnecting from the server.

        Args:
            exc_type (Exception): The exception type, if any.
            exc_val (Any): The exception value, if any.
            exc_tb (Traceback): The traceback, if any.

        Raises:
            MilvusAPIError: If disconnection fails.
        """
        try:
            if exc_type is not None:
                # Extract and format the traceback
                extracted_frames = traceback.extract_tb(exc_tb)
                formatted_traceback = "".join(traceback.format_list(extracted_frames))
                log.error(f"\nException type: {exc_type}, \nvalue: {exc_val}")
                log.error(f"Traceback: {formatted_traceback}")
            if self._initialized:
                await self.disconnect()
                self._initialized = False
                log.info("Disconnected from Milvus server.")
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")

    @async_log_decorator
    def __await__(self):
        """Makes the class awaitable for async contexts.

        Returns:
            Coroutine: The awaitable coroutine.
        """
        log.info("Awaiting connection to the Milvus server.")
        return  self.__aenter__()


class CollectionAPI(ICollectionAPI):
    """
    Manages Milvus collections with methods for creation, listing, describing, and dropping.

    Implements the ICollectionAPI interface to handle collection-related operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_collection: Creates a new collection.
        list_collections: Lists all collections in a database.
        describe_collection: Describes a specific collection.
        drop_collection: Drops a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = CollectionAPI(connect_api)
        fields = [FieldSchema(name="id", dtype=DataType.INT64, is_primary=True)]
        await api.create_collection("test_collection", fields, "test_db")
        ```

    Raises:
        MilvusAPIError: If collection operations fail.
        MilvusValidationError: If input parameters are invalid.
    """
    _connect_api: IConnectAPI = None

    def __init__(self, connect_api: IConnectAPI):
        """Initializes CollectionAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    # Private helper function
    @async_log_decorator
    async def _build_collection_schema(self,
                                 collection_name: str,
                                 fields: List[FieldSchema],
                                 dimension: Union[int, None],
                                 primary_field_name: str,
                                 id_type: str,
                                 vector_field_name: str,
                                 auto_id: bool) -> CollectionSchema:
        """
        Builds a CollectionSchema for the specified collection.

        Args:
            collection_name (str): Name of the collection.
            fields (List[FieldSchema]): List of field schemas.
            dimension (int | None): Vector field dimension if added automatically.
            primary_field_name (str): Name of the primary key field.
            id_type (str): Type of primary key ("int" or "string").
            vector_field_name (str): Name of the vector field.
            auto_id (bool): Whether to auto-generate IDs for the primary key.

        Returns:
            CollectionSchema: The constructed collection schema.

        Raises:
            MilvusValidationError: If input validation fails.
        """
        vector_dtypes = {DataType.FLOAT_VECTOR, DataType.BINARY_VECTOR}
        fields_list = list(fields)

        # Add primary key if not present
        if not any(f.is_primary for f in fields_list):
            if id_type == "int":
                dtype = DataType.INT64
            elif id_type == "string":
                dtype = DataType.VARCHAR
            else:
                raise MilvusValidationError(f"Unsupported id_type: {id_type}")
            primary_field = FieldSchema(
                name=primary_field_name,
                dtype=dtype,
                is_primary=True,
                auto_id=auto_id,
                max_length=256 if id_type == "string" else None,
                description="Auto-added primary key field"
            )
            fields_list.insert(0, primary_field)
            log.debug(f"Added primary key field: {primary_field_name}")

        # Add vector field if not present
        if not any(f.dtype in vector_dtypes for f in fields_list):
            if dimension is None:
                raise MilvusValidationError("Dimension must be provided if no vector field is in fields")
            vector_field = FieldSchema(
                name=vector_field_name,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Auto-added vector field"
            )
            fields_list.append(vector_field)
            log.debug(f"Added vector field: {vector_field_name}")

        # Create the collection schema
        collection_schema = CollectionSchema(
            fields=fields_list,
            description=f"Collection {collection_name} schema"
        )
        log.info(f"Created collection schema for {collection_name}, schema: {collection_schema}")
        return collection_schema

    @async_log_decorator
    async def create_collection(self,
                                collection_name: str,
                                fields: List[FieldSchema],
                                database_name: str = "default",
                                dimension: Union[int, None] = None,
                                primary_field_name: str = "id",
                                id_type: str = "int",
                                vector_field_name: str = "vector",
                                metric_type: str = "COSINE",
                                auto_id: bool = False,
                                timeout: Union[float, None] = None,
                                schema: Union[CollectionSchema, None] = None,
                                index_params: Union[Dict, None] = None,
                                **kwargs) -> Collection:
        """Creates a new collection in the specified database.

        Args:
            collection_name (str): Name of the collection.
            fields (List[FieldSchema]): Field schemas.
            database_name (str): Database name. Defaults to "default".
            dimension (int | None): Vector dimension if auto-added.
            primary_field_name (str): Primary key name. Defaults to "id".
            id_type (str): Primary key type. Defaults to "int".
            vector_field_name (str): Vector field name. Defaults to "vector".
            metric_type (str): Index metric type. Defaults to "COSINE".
            auto_id (bool): Auto-generate IDs. Defaults to False.
            timeout (float | None): Operation timeout.
            schema (CollectionSchema | None): Pre-defined schema.
            index_params (Dict | None): Index parameters.
            **kwargs: Additional arguments.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If collection creation fails.
        """
        # Validate inputs
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if schema is None and (not fields or not all(isinstance(f, FieldSchema) for f in fields)):
            raise MilvusValidationError(
                "Fields must be a non-empty list of FieldSchema objects when schema is not provided")
        if schema is not None and not isinstance(schema, CollectionSchema):
            raise MilvusValidationError("Schema must be a CollectionSchema object")

        try:
            # Use the provided schema or build one
            collection_schema = schema or await self._build_collection_schema(
                collection_name=collection_name,
                fields=fields,
                dimension=dimension,
                primary_field_name=primary_field_name,
                id_type=id_type,
                vector_field_name=vector_field_name,
                auto_id=auto_id
            )

            # Update and add to kwargs arguments
            create_kwargs = {"db_name": database_name}
            if timeout is not None:
                create_kwargs["timeout"] = timeout
            create_kwargs.update(kwargs)

            # Create the collection
            await self._connect_api.async_client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                schema=collection_schema,
                **create_kwargs
            )
            log.info(f"Created collection: {collection_name}, Database: {database_name}")

            # Instantiate the collection object
            collection = Collection(
                name=collection_name,
                schema=collection_schema,
                using=database_name,
                **{"collection.ttl.seconds": 1800}
            )

            # Create index if specified
            if index_params is not None:
                vector_fields = [f.name for f in collection_schema.fields if
                                 f.dtype in {DataType.FLOAT_VECTOR, DataType.BINARY_VECTOR}]
                if vector_field_name not in vector_fields:
                    raise MilvusValidationError(f"Vector field {vector_field_name} not found in schema")
                index_params = dict(index_params)  # Copy to avoid modifying input
                if "metric_type" not in index_params:
                    index_params["metric_type"] = metric_type
                status = collection.create_index(
                    field_name=vector_field_name,
                    index_params=index_params,
                    index_name=f"{collection_name}_{vector_field_name}_idx",
                    timeout=timeout
                )
                log.debug(f"Created index status: {status}")
                log.info(f"Created index on {vector_field_name} with params: {index_params}")

            return collection
        except MilvusException as e:
            log.error(f"Failed to create collection: {e}")
            raise MilvusAPIError(f"Collection creation failed: {e}")

    @async_log_decorator
    async def list_collections(self, database_name: str = "default") -> List[str]:
        """Lists all collections in the specified database.

        Args:
            database_name (str): Database name. Defaults to "default".

        Returns:
            List[str]: List of collection names.

        Raises:
            MilvusAPIError: If listing fails.
        """
        try:
            collections = await self._connect_api.async_client.list_collections(db_name=database_name)
            log.info(f"Listed {len(collections)} collections in database {database_name}")
            return collections
        except MilvusException as e:
            log.error(f"Failed to list collections: {e}")
            raise MilvusAPIError(f"List collections failed: {e}")

    @async_log_decorator
    async def describe_collection(self, collection_name: str, database_name: str = "default") -> Dict[str, Any]:
        """Describes the specified collection.

        Args:
            collection_name (str): Name of the collection.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict[str, Any]: Collection description.

        Raises:
            MilvusAPIError: If description fails.
        """
        try:
            desc = await self._connect_api.async_client.describe_collection(
                collection_name=collection_name,
                db_name=database_name
            )
            log.info(f"Described collection {collection_name}")
            return desc
        except MilvusException as e:
            log.error(f"Failed to describe collection: {e}")
            raise MilvusAPIError(f"Describe collection failed: {e}")

    @async_log_decorator
    async def drop_collection(self, collection_name: str, timeout: float = 10) -> Dict[str, str]:
        """Drops the specified collection.

        Args:
            collection_name (str): Name of the collection.
            timeout (str): Database name. Defaults to "default".

        Returns:
            Dict[str, str]: Status message and result.

        Raises:
            MilvusAPIError: If dropping fails.
        """
        try:
            await self._connect_api.async_client.drop_collection(
                collection_name=collection_name,
                timeout= timeout
            )
            log.info(f"Dropped collection {collection_name} from database {timeout}")
            return {"message": f"Collection {collection_name} dropped", "status": "success"}
        except MilvusException as e:
            log.error(f"Failed to drop collection: {e}")
            raise MilvusAPIError(f"Drop collection failed: {e}")

class VectorAPI(IVectorAPI):
    """
    Handles vector operations like insertion and deletion in Milvus.

    Implements the IVectorAPI interface to manage vector data.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        insert: Inserts entities into a collection.
        delete: Deletes entities from a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = VectorAPI(connect_api)
        await api.insert("test_collection", [{"vector": [0.1] * 128}])
        ```

    Raises:
        MilvusAPIError: If vector operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes VectorAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    async def insert(self, collection_name: str, entities: List[Dict[str, Any]], partition_name: Optional[str] = None,
                     database_name: str = "default") -> Dict:
        """Inserts entities into a collection.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        Returns:
            List[int]: List of primary keys for inserted entities.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If insertion fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not entities or not all(isinstance(e, dict) for e in entities):
            raise MilvusValidationError("Entities must be a non-empty list of dictionaries")
        try:
            collection = Collection(
                name=collection_name,
                using=self._connect_api._alias
            )
            # MR: MilvusResultS
            mr: dict = await self._connect_api.async_client.insert(
                collection_name=collection_name,
                data=entities,
                partition_name=partition_name,
                db_name=database_name
            )
            log.debug(f"Insert result: {mr}")
            collection.flush()
            log.info(f"Inserted {len(entities)} entities into {collection_name}")
            return mr
        except MilvusException as e:
            log.error(f"Failed to insert entities: {e}")
            raise MilvusAPIError(f"Insert failed: {e}")

    @async_log_decorator
    async def delete(self, collection_name: str, expr: str, partition_name: Optional[str] = None,
                     database_name: str = "default"):
        """Deletes entities from a collection based on an expression.

        Args:
            collection_name (str): Name of the collection.
            expr (str): Expression to filter entities for deletion.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If deletion fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not expr or not isinstance(expr, str):
            raise MilvusValidationError("Expression must be a non-empty string")
        try:
            await self._connect_api.async_client.delete(
                collection_name=collection_name,
                expr=expr,
                partition_name=partition_name,
                db_name=database_name
            )
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            await collection.flush()
            log.info(f"Deleted entities from {collection_name} with expression: {expr}")
        except MilvusException as e:
            log.error(f"Failed to delete entities: {e}")
            raise MilvusAPIError(f"Delete failed: {e}")

class SearchAPI(ISearchAPI):
    """
    Manages vector searches in Milvus with optional reranking.

    Implements the ISearchAPI interface to handle search operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        search: Performs a vector search in a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = SearchAPI(connect_api)
        results = await api.search("test_collection", [[0.1] * 128], "vector", {"metric_type": "COSINE"}, 5)
        ```

    Raises:
        MilvusAPIError: If search operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes SearchAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    async def search(self,
                     collection_name: str, data: List[List[float]],
                     anns_field: str, param: Dict[str, Any],
                     limit: int, expr: Optional[str] = None,
                     output_fields: Optional[List[str]] = None,
                     partition_names: Optional[List[str]] = None,
                     database_name: str = "default",
                     rerank: bool = False, **kwargs) -> List[Dict]:
        """Performs a vector search in the specified collection.

        Args:
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            param (Dict[str, Any]): Search parameters (e.g., metric_type).
            limit (int): Maximum number of results.
            expr (Optional[str]): Filter expression. Defaults to None.
            output_fields (Optional[List[str]]): Fields to return. Defaults to None.
            partition_names (Optional[List[str]]): Partitions to search. Defaults to None.
            database_name (str): Database name. Defaults to "default".
            rerank (bool): Whether to rerank results by distance. Defaults to False.
            **kwargs: Additional search arguments.

        Returns:
            List[Dict]: Search results with IDs and distances.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If search fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not data or not all(isinstance(v, list) for v in data):
            raise MilvusValidationError("Data must be a non-empty list of lists")
        if not anns_field or not isinstance(anns_field, str):
            raise MilvusValidationError("ANNS field must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            collection.load()
            # Search the database
            results = await self._connect_api.async_client.search(
                collection_name=collection_name,
                data=data,
                anns_field=anns_field,
                search_params=param,
                limit=limit,
                filter=expr,
                output_fields=output_fields,
                partition_names=partition_names,
                db_name=database_name,
                **kwargs
            )
            # Get the results at index 0
            results = results[0]
            log.debug(f"Contents of results: {results}, "
                      f"\nAttributes of results: {dir(results)}, "
                      f"\nType of results: {type(results)}, "
                      f"\nLength of results: {len(results)}, "
                      f"\nContains distance: {'distance' in str(results)}")

            # Check if reranking is needed
            if rerank and "distance" in str(results):
                log.info(f"Reranking {len(results)} results by distance")
                results = await self._rerank_results(results)

            log.info(f"Completed search in {collection_name}, \nResults: {results}")
            return results
        except MilvusException as e:
            log.error(f"Failed to search: {e}")
            raise MilvusAPIError(f"Search failed: {e}")

    @async_log_decorator
    async def _rerank_results(self, results: List[Dict]) -> List[Dict]:
        """Reranks search results by distance.

        Args:
            results (List[Dict]): Original search results.

        Returns:
            List[Dict]: Reranked results.
        """
        return sorted(results, key=lambda x: x["distance"])

class IndexAPI(IIndexAPI):
    """
    Handles index creation and deletion in Milvus.

    Implements the IIndexAPI interface to manage indexes on collection fields.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_index: Creates an index on a field.
        drop_index: Drops an index from a field.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = IndexAPI(connect_api)
        await api.create_index("test_collection", "vector", {"index_type": "IVF_FLAT"})
        ```

    Raises:
        MilvusAPIError: If index operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes IndexAPI with a connection instance."""
        self._connect_api = connect_api

    @async_log_decorator
    async def create_index(self, collection_name: str, field_name: str, index_params: Dict,
                           database_name: str = "default", **kwargs):
        """Creates an index on a field in a collection.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field to index.
            index_params (Dict): Index parameters.
            database_name (str): Database name. Defaults to "default".
            **kwargs: Additional index arguments.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If index creation fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not field_name or not isinstance(field_name, str):
            raise MilvusValidationError("Field name must be a non-empty string")
        if not index_params or not isinstance(index_params, dict):
            raise MilvusValidationError("Index parameters must be a non-empty dictionary")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            await collection.create_index(field_name=field_name, index_params=index_params, **kwargs)
            log.info(f"Created index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to create index: {e}")
            raise MilvusAPIError(f"Index creation failed: {e}")

    @async_log_decorator
    async def drop_index(self, collection_name: str, field_name: str, database_name: str = "default"):
        """Drops an index from a field in a collection.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field with the index.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If index drop fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not field_name or not isinstance(field_name, str):
            raise MilvusValidationError("Field name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            await collection.drop_index(field_name=field_name)
            log.info(f"Dropped index on {field_name} in {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to drop index: {e}")
            raise MilvusAPIError(f"Index drop failed: {e}")

class PartitionAPI(IPartitionAPI):
    """
    Manages partitions within Milvus collections.

    Implements the IPartitionAPI interface to handle partition creation and deletion.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_partition: Creates a partition in a collection.
        drop_partition: Drops a partition from a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = PartitionAPI(connect_api)
        await api.create_partition("test_collection", "partition1")
        ```

    Raises:
        MilvusAPIError: If partition operations fail.
        MilvusValidationError: If input parameters are invalid.
    """
    def __init__(self, connect_api: IConnectAPI):
        """Initializes PartitionAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def create_partition(self, collection_name: str, partition_name: str, database_name: str = "default"):
        """Creates a partition in a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If partition creation fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not partition_name or not isinstance(partition_name, str):
            raise MilvusValidationError("Partition name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            partition =  collection.create_partition(partition_name=partition_name)
            log.info(f"Created partition {partition_name} in {collection_name}, \nPartition: {partition}")
        except MilvusException as e:
            log.error(f"Failed to create partition: {e}")
            raise MilvusAPIError(f"Partition creation failed: {e}")

    @async_log_decorator
    async def drop_partition(self, collection_name: str, partition_name: str, database_name: str = "default"):
        """Drops a partition from a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If partition drop fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        if not partition_name or not isinstance(partition_name, str):
            raise MilvusValidationError("Partition name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            await collection.drop_partition(partition_name=partition_name)
            log.info(f"Dropped partition {partition_name} from {collection_name}")
        except MilvusException as e:
            log.error(f"Failed to drop partition: {e}")
            raise MilvusAPIError(f"Partition drop failed: {e}")

class StatAPI(IStatAPI):
    """
    Retrieves statistics for Milvus collections.

    Implements the IStatAPI interface to provide collection statistics.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        get_collection_stats: Retrieves statistics for a collection.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = StatAPI(connect_api)
        stats = await api.get_collection_stats("test_collection")
        ```

    Raises:
        MilvusAPIError: If statistics retrieval fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes StatAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def get_collection_stats(self, collection_name: str, database_name: str = "default") -> Dict[str, Any]:
        """Gets statistics for a collection.

        Args:
            collection_name (str): Name of the collection.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict[str, Any]: Collection statistics.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If stats retrieval fails.
        """
        if not collection_name or not isinstance(collection_name, str):
            raise MilvusValidationError("Collection name must be a non-empty string")
        try:
            collection = Collection(collection_name, using=self._connect_api._alias, db_name=database_name)
            stats = await collection.stats
            log.info(f"Retrieved stats for {collection_name}")
            return stats
        except MilvusException as e:
            log.error(f"Failed to retrieve stats: {e}")
            raise MilvusAPIError(f"Stats retrieval failed: {e}")

class MonitorAPI(IMonitorAPI):
    """
    Provides monitoring information for the Milvus server.

    Implements the IMonitorAPI interface to retrieve server metrics.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        get_monitor_info: Retrieves monitoring information.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = MonitorAPI(connect_api)
        info = await api.get_monitor_info()
        ```

    Raises:
        MilvusAPIError: If monitoring information retrieval fails.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes MonitorAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def get_monitor_info(self) -> Dict[str, Any]:
        """Gets monitoring information for the Milvus server.

        Returns:
            Dict[str, Any]: Monitoring metrics including server version and collection stats.

        Raises:
            MilvusAPIError: If info retrieval fails.
        """
        try:
            server_version = await utility.get_server_version()
            connection_status = self._connect_api.async_client is not None
            collections = await self._connect_api.async_client.list_collections()
            collection_stats = {}
            for col_name in collections:
                try:
                    collection = Collection(col_name, using=self._connect_api._alias)
                    stats = {
                        "num_entities": await collection.num_entities,
                        "has_index": await collection.has_index(),
                        "partitions": len(await collection.partitions)
                    }
                    collection_stats[col_name] = stats
                except MilvusException as e:
                    log.warning(f"Failed to retrieve stats for collection {col_name}: {e}")
            metrics = {
                "server_version": server_version,
                "connection_status": connection_status,
                "timestamp": datetime.datetime.now().isoformat(),
                "collections": collection_stats,
                "collection_count": len(collections)
            }
            log.info(f"Retrieved Milvus server metrics: version={server_version}, collections={len(collections)}")
            return metrics
        except MilvusException as e:
            log.error(f"Failed to retrieve monitor info: {e}")
            raise MilvusAPIError(f"Monitor info retrieval failed: {e}")

class EmbeddingAPI(IEmbeddingAPI):
    """
    Generates embeddings using a provided model for Milvus.

    Implements the IEmbeddingAPI interface to handle embedding generation.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        generate_embeddings: Generates embeddings for data.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = EmbeddingAPI(connect_api)
        embeddings = await api.generate_embeddings(["text"], lambda x: np.array([[0.1] * 128]))
        ```

    Raises:
        MilvusAPIError: If embedding generation fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes EmbeddingAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def generate_embeddings(self, data: List[Any], embedding_model: Callable[[List[Any]], np.ndarray],
                                  embedding_type: str = "float", batch_size: int = 32) -> np.ndarray:
        """Generates embeddings for the provided data.

        Args:
            data (List[Any]): Data to embed (e.g., text, images).
            embedding_model (Callable[[List[Any]], np.ndarray]): Model to generate embeddings.
            embedding_type (str): Type of embeddings ("float" or "binary"). Defaults to "float".
            batch_size (int): Number of items per batch. Defaults to 32.

        Returns:
            np.ndarray: Generated embeddings.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If embedding generation fails.
        """
        if not data:
            raise MilvusValidationError("Data must be a non-empty list")
        if not callable(embedding_model):
            raise MilvusValidationError("Embedding model must be a callable function")
        if embedding_type not in ["float", "binary"]:
            raise MilvusValidationError(f"Unsupported embedding type: {embedding_type}")
        try:
            embeddings = []
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_embeddings = embedding_model(batch)
                if not isinstance(batch_embeddings, np.ndarray):
                    raise MilvusValidationError("Embedding model must return a NumPy array")
                if embedding_type == "binary":
                    batch_embeddings = (batch_embeddings > 0.5).astype(np.uint8)
                embeddings.append(batch_embeddings)
            result = np.concatenate(embeddings, axis=0)
            log.info(f"Generated embeddings for {len(data)} items")
            return result
        except Exception as e:
            log.error(f"Failed to generate embeddings: {e}")
            raise MilvusAPIError(f"Embedding generation failed: {e}")

class AdminAPI(IAdminAPI):
    """
    Manages administrative tasks in Milvus, such as user management.

    Implements the IAdminAPI interface to handle administrative operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        create_user: Creates a new user.
        list_users: Lists all users.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = AdminAPI(connect_api)
        await api.create_user("new_user", "password")
        ```

    Raises:
        MilvusAPIError: If administrative operations fail.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes AdminAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def create_user(self, username: str, password: str):
        """Creates a new user in Milvus.

        Args:
            username (str): Username for the new user.
            password (str): Password for the new user.

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If user creation fails.
        """
        if not username or not isinstance(username, str) or not password or not isinstance(password, str):
            raise MilvusValidationError("Username and password must be non-empty strings")
        try:
            await self._connect_api.async_client.create_user(username, password)
            log.info(f"Created user {username}")
        except MilvusException as e:
            log.error(f"Failed to create user: {e}")
            raise MilvusAPIError(f"User creation failed: {e}")

    @async_log_decorator
    async def list_users(self) -> List[str]:
        """Lists all users in Milvus.

        Returns:
            List[str]: List of usernames.

        Raises:
            MilvusAPIError: If listing fails.
        """
        try:
            users = await self._connect_api.async_client.list_users()
            log.info(f"Listed {len(users)} users")
            return users
        except MilvusException as e:
            log.error(f"Failed to list users: {e}")
            raise MilvusAPIError(f"List users failed: {e}")

class DataImportAPI(IDataImportAPI):
    """
    Handles data imports into Milvus collections.

    Implements the IDataImportAPI interface to manage data import operations.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.

    Methods:
        import_data: Imports data into a collection from a file.

    Example:
        ```python
        connect_api = ConnectAPI()
        api = DataImportAPI(connect_api)
        await api.import_data("test_collection", "data.json")
        ```

    Raises:
        MilvusAPIError: If data import fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes DataImportAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): The connection API instance for Milvus operations.
        """
        self._connect_api = connect_api

    @async_log_decorator
    async def import_data(self, collection_name: str, file_path: str, database_name: str = "default"):
        """Imports data into a collection from a file.

        Args:
            collection_name (str): Name of the collection.
            file_path (str): Path to the data file.
            database_name (str): Database name. Defaults to "default".

        Raises:
            MilvusValidationError: If inputs are invalid.
            MilvusAPIError: If import fails.
        """
        if not collection_name or not isinstance(collection_name, str) or not file_path or not isinstance(file_path, str):
            raise MilvusValidationError("Collection name and file path must be non-empty strings")
        try:
            await self._connect_api.async_client.import_data(
                collection_name=collection_name,
                file_path=file_path,
                db_name=database_name
            )
            log.info(f"Imported data into {collection_name} from {file_path}")
        except MilvusException as e:
            log.error(f"Failed to import data: {e}")
            raise MilvusAPIError(f"Data import failed: {e}")

class MilvusAPI:
    """
    Facade class integrating all Milvus APIs for a unified interface.

    Provides a simplified API for interacting with Milvus, supporting operations like
    collection management, vector operations, searches, and administration.

    Attributes:
        _connect_api (IConnectAPI): The connection API instance.
        _collection_api (CollectionAPI): The collection API instance.
        _vector_api (VectorAPI): The vector API instance.
        _search_api (SearchAPI): The search API instance.
        _index_api (IndexAPI): The index API instance.
        _partition_api (PartitionAPI): The partition API instance.
        _stat_api (StatAPI): The statistics API instance.
        _monitor_api (MonitorAPI): The monitoring API instance.
        _embedding_api (EmbeddingAPI): The embedding API instance.
        _admin_api (AdminAPI): The admin API instance.
        _data_import_api (DataImportAPI): The data import API instance.

    Methods:
        create_collection: Creates a new collection.
        drop_collection: Drops a collection.
        insert: Inserts entities into a collection.
        delete: Deletes entities from a collection.
        search: Searches for vectors in a collection.
        create_index: Creates an index on a field.
        drop_index: Drops an index from a field.
        create_partition: Creates a partition in a collection.
        drop_partition: Drops a partition from a collection.
        get_collection_stats: Gets collection statistics.
        get_monitor_info: Gets server monitoring information.
        generate_embeddings: Generates embeddings for data.
        create_user: Creates a new user.
        list_users: Lists all users.
        import_data: Imports data into a collection.

    Example:
        ```python
        async def main():
            async with ConnectAPI(host="localhost", port="19530") as connect_api:
                api = MilvusAPI(connect_api)
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
                ]
                await api.create_collection("test_collection", fields, dimension=128)
                await api.drop_collection("test_collection")
        asyncio.run(main())
        ```

    Raises:
        MilvusAPIError: If any operation fails.
        MilvusValidationError: If input parameters are invalid.
    """

    def __init__(self, connect_api: IConnectAPI):
        """Initializes MilvusAPI with a connection instance.

        Args:
            connect_api (IConnectAPI): Connection API instance.
        """
        self._connect_api = connect_api
        self._collection_api = CollectionAPI(self._connect_api)
        self._vector_api = VectorAPI(self._connect_api)
        self._search_api = SearchAPI(self._connect_api)
        self._index_api = IndexAPI(self._connect_api)
        self._partition_api = PartitionAPI(self._connect_api)
        self._stat_api = StatAPI(self._connect_api)
        self._monitor_api = MonitorAPI(self._connect_api)
        self._embedding_api = EmbeddingAPI(self._connect_api)
        self._admin_api = AdminAPI(self._connect_api)
        self._data_import_api = DataImportAPI(self._connect_api)
        log.info("MilvusAPI initialized...")

    @async_log_decorator
    async def create_collection(self, collection_name: str,
                                fields: List[FieldSchema],
                                database_name: str = "default",
                                dimension: Union[int, None] = None,
                                primary_field_name: str = "id",
                                id_type: str = "int",
                                vector_field_name: str = "vector",
                                metric_type: str = "COSINE",
                                auto_id: bool = False,
                                timeout: Union[float, None] = None,
                                schema: Union[CollectionSchema, None] = None,
                                index_params: Union[Dict, None] = None, **kwargs) -> Collection:
        """Creates a new collection.

        Args:
            collection_name (str): Name of the collection.
            fields (List[FieldSchema]): Field schemas.
            database_name (str): Database name. Defaults to "default".
            dimension (int | None): Vector dimension if auto-added.
            primary_field_name (str): Primary key name. Defaults to "id".
            id_type (str): Primary key type. Defaults to "int".
            vector_field_name (str): Vector field name. Defaults to "vector".
            metric_type (str): Index metric type. Defaults to "COSINE".
            auto_id (bool): Auto-generate IDs. Defaults to False.
            timeout (float | None): Operation timeout.
            schema (CollectionSchema | None): Pre-defined schema.
            index_params (Dict | None): Index parameters.
            **kwargs: Additional arguments.

        Returns:
            Collection: Created collection object.

        Raises:
            MilvusAPIError: If creation fails.
        """
        try:
            return await self._collection_api.create_collection(
                collection_name=collection_name,
                fields=fields,
                database_name=database_name,
                dimension=dimension,
                primary_field_name=primary_field_name,
                id_type=id_type,
                vector_field_name=vector_field_name,
                metric_type=metric_type,
                auto_id=auto_id,
                timeout=timeout,
                schema=schema,
                index_params=index_params,
                **kwargs
            )
        except MilvusException as e:
            log.error(f"Failed to create collection: {e}")
            raise MilvusAPIError(f"Collection creation failed: {e}")

    @async_log_decorator
    async def drop_collection(self, collection_name: str, timeout: float = 10) -> Dict[str, str]:
        """Drops a collection.

        Args:
            collection_name (str): Name of the collection.
            timeout (float): Operation timeout. Defaults to 10.

        Returns:
            Dict[str, str]: Status of the drop operation.

        """
        return await self._collection_api.drop_collection(collection_name, timeout=timeout)

    @async_log_decorator
    async def insert(self, collection_name: str, entities: List[Dict[str, Any]], partition_name: Optional[str] = None,
                     database_name: str = "default") -> Dict:
        """Inserts entities into a collection.

        Args:
            collection_name (str): Name of the collection.
            entities (List[Dict[str, Any]]): Entities to insert.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict: Insertion result.

        """
        return await self._vector_api.insert(collection_name, entities, partition_name, database_name)

    @async_log_decorator
    async def delete(self, collection_name: str, expr: str, partition_name: Optional[str] = None,
                     database_name: str = "default") -> None:
        """Deletes entities from a collection.

        Args:
            collection_name (str): Name of the collection.
            expr (str): Expression to filter entities for deletion.
            partition_name (Optional[str]): Partition name. Defaults to None.
            database_name (str): Database name. Defaults to "default".
        """
        await self._vector_api.delete(collection_name, expr, partition_name, database_name)

    @async_log_decorator
    async def search(self, collection_name: str, data: List[List[float]], anns_field: str, search_params: Dict[str, Any],
                     limit: int, expr: Optional[str] = None, output_fields: Optional[List[str]] = None,
                     partition_names: Optional[List[str]] = None, database_name: str = "default",
                     rerank: bool = False, **kwargs) -> List[Dict]:
        """Searches for vectors in a collection.

        Args:
            collection_name (str): Name of the collection.
            data (List[List[float]]): Query vectors.
            anns_field (str): Field to search against.
            search_params (Dict[str, Any]): Search parameters.
            limit (int): Maximum number of results.
            expr (Optional[str]): Filter expression. Defaults to None.
            output_fields (Optional[List[str]]): Fields to return. Defaults to None.
            partition_names (Optional[List[str]]): Partitions to search. Defaults to None.
            database_name (str): Database name. Defaults to "default".
            rerank (bool): Whether to rerank results. Defaults to False.
            **kwargs: Additional search parameters.

        Returns:
            List[Dict]: Search results.
        """
        return await self._search_api.search(
            collection_name,
            data,
            anns_field,
            search_params,
            limit,
            expr,
            output_fields,
            partition_names,
            database_name,
            rerank,
            **kwargs)

    @async_log_decorator
    async def create_index(self,
                           collection_name: str, field_name: str,
                           index_params: Dict, database_name: str = "default", **kwargs) -> None:
        """Creates an index on a field.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field to index.
            index_params (Dict): Index parameters.
            database_name (str): Database name. Defaults to "default".
            **kwargs: Additional index parameters.

        """
        await self._index_api.create_index(collection_name, field_name, index_params, database_name, **kwargs)

    @async_log_decorator
    async def drop_index(self, collection_name: str, field_name: str, database_name: str = "default") -> None:
        """Drops an index from a field.

        Args:
            collection_name (str): Name of the collection.
            field_name (str): Field with the index.
            database_name (str): Database name. Defaults to "default".
        """
        await self._index_api.drop_index(collection_name, field_name, database_name)

    @async_log_decorator
    async def create_partition(self, collection_name: str, partition_name: str, database_name: str = "default") -> None:
        """Creates a partition in a collection.

        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".
        """
        await self._partition_api.create_partition(collection_name, partition_name, database_name)

    @async_log_decorator
    async def drop_partition(self, collection_name: str, partition_name: str, database_name: str = "default") -> None:
        """Drops a partition from a collection.
        Args:
            collection_name (str): Name of the collection.
            partition_name (str): Name of the partition.
            database_name (str): Database name. Defaults to "default".
        """
        await self._partition_api.drop_partition(collection_name, partition_name, database_name)

    @async_log_decorator
    async def get_collection_stats(self, collection_name: str, database_name: str = "default") -> Dict[str, Any]:
        """Gets collection statistics.

        Args:
            collection_name (str): Name of the collection.
            database_name (str): Database name. Defaults to "default".

        Returns:
            Dict[str, Any]: Collection statistics.
        """
        return await self._stat_api.get_collection_stats(collection_name, database_name)

    @async_log_decorator
    async def get_monitor_info(self) -> Dict[str, Any]:
        """
        Gets server monitoring information.

        Returns:
            Dict[str, Any]: Monitoring metrics.

        """
        return await self._monitor_api.get_monitor_info()

    @async_log_decorator
    async def generate_embeddings(self, data: List[Any], embedding_model: Callable[[List[Any]], np.ndarray],
                                  embedding_type: str = "float", batch_size: int = 32) -> np.ndarray:
        """
        Generates embeddings for data.

        Args:
            data (List[Any]): Data to embed.
            embedding_model (Callable[[List[Any]], np.ndarray]): Model to generate embeddings.
            embedding_type (str): Type of embeddings. Defaults to "float".
            batch_size (int): Number of items per batch. Defaults to 32.

        Returns:
            np.ndarray: Generated embeddings.
        """
        return await self._embedding_api.generate_embeddings(data, embedding_model, embedding_type, batch_size)

    @async_log_decorator
    async def create_user(self, username: str, password: str) -> None:
        """
        Creates a new user.

        Args:
            username (str): Username for the new user.
            password (str): Password for the new user.
        """
        await self._admin_api.create_user(username, password)

    @async_log_decorator
    async def list_users(self) -> List[str]:
        """
        Lists all users.

        Returns:
            List[str]: List of usernames.
        """
        return await self._admin_api.list_users()

    @async_log_decorator
    async def import_data(self, collection_name: str, file_path: str, database_name: str = "default") -> None:
        """
        Imports data into a collection.

        Args:
            collection_name (str): Name of the collection.
            file_path (str): Path to the data file.
            database_name (str): Database name. Defaults to "default".

        """
        await self._data_import_api.import_data(collection_name, file_path, database_name)


class AsyncMilvusClientWrapper(utility.connections):
    """
    A wrapper for AsyncMilvusClient to provide additional functionality.

    Args:
        uri (str): Milvus server URI. Defaults to "http://localhost:19530".
        user (str): Username for authentication. Defaults to an empty string.
        password (str): Password for authentication. Defaults to an empty string.
        db_name (str): Database name. Defaults to an empty string.
        token (str): Token for authentication. Defaults to an empty string.
        timeout (Optional[float]): Timeout for requests. Defaults to None.
        **kwargs (Any): Additional arguments for the client.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures a singleton instance of ConnectAPI.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            ConnectAPI: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            log.info("New ConnectAPI instance created.")
        return cls._instance

    def __init__(self,
                 uri: str = "http://localhost:19530",
                 user: str = "",
                 password: str = "",
                 db_name: str = "",
                 host: str = "localhost",
                 port: int = 19530,
                 token: str = "",
                 timeout: Optional[float] = None,
                 **kwargs: Any) -> None:
        if not hasattr(self, '_initialized') or not self._initialized:
            super().__init__(self, uri=uri,
                             user=user,
                             password=password,
                             db_name=db_name,
                             token=token,
                             timeout=timeout,
                             **kwargs)
            self._uri = uri
            self._alias = kwargs.get("alias", "default")
            self._user = user
            self._password = password
            self._host = host
            self._port = port
            self._timeout = timeout
            self._db_name = db_name
            self._token = token
            self._config_manager = ConfigManager({
                "host": self._host,
                "port": self._port,
                "user": self._user,
                "password": self._password,
                "timeout": self._timeout,
                "db_name": self._db_name,
                "token": self._token,
                "encryption_key": os.environ.get("MILVUS_ENCRYPT_KEY"),
            })
            self._security_manager = SecurityManager(self._config_manager)
            self._initialized = True
            log.info(f"AsyncMilvusClientWrapper initialized with URI: {self._uri}")
        else:
            log.warning("AsyncMilvusClientWrapper instance already exists. Using existing parameters.")

    @async_log_decorator
    async def has_collection(self, collection_name: str,
                             using: str = "default",
                             timeout: Optional[float] = None) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name (str): Name of the collection.
            using (str): The alias of the connection to use. Defaults to "default".
            timeout (Optional[float]): Timeout for the operation. Defaults to None.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        return await utility.has_collection(collection_name=collection_name, using=using, timeout=timeout)

    async def __aenter__(self):
        """
        Enter the runtime context related to this object.

        Returns:
            self: The instance of AsyncMilvusClientWrapper.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the runtime context related to this object.

        Args:
            exc_type (type): The exception type.
            exc_val (Exception): The exception value.
            exc_tb (traceback): The traceback object.

        Raises:
            MilvusAPIError: If disconnection fails.
        """
        try:
            if exc_type is not None:
                # Extract and format the traceback
                extracted_frames = traceback.extract_tb(exc_tb)
                formatted_traceback = "".join(traceback.format_list(extracted_frames))
                log.error(f"\nException type: {exc_type}, \nvalue: {exc_val}")
                log.error(f"Traceback: {formatted_traceback}")
            if self._initialized:
                await self.close()
                self._initialized = False
                log.info("Disconnected from Milvus server.")
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")

    def __dict__(self):
        return {
            "uri": self._uri,
            "alias": self._alias,
            "user": self._user,
            "password": self._password,
            "host": self._host,
            "port": self._port,
            "timeout": self._timeout,
            "db_name": self._db_name,
            "token": self._token,
            "config_manager": self._config_manager,
            "security_manager": self._security_manager,
            "initialized": self._initialized
        }

    def __repr__(self):
        return f"AsyncMilvusClientWrapper({self.__dict__()})"

    def __str__(self):
        """String representation of the AsyncMilvusClientWrapper."""
        return f"AsyncMilvusClientWrapper({self.__dict__()})"


