#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/milvus/connect.py
"""
ConnectAPI and AsyncMilvusClientWrapper
Handles connections to the Milvus server using synchronous and asynchronous operations.
Implements the IConnectAPI interface to manage connection establishment and disconnection.
Uses the Singleton pattern to ensure a single connection instance.

Key Features:
- Connect to Milvus server with retry logic.
- Create and check databases.
- Context manager support for automatic connection management.
- Asynchronous support for non-blocking operations.
- Singleton pattern to ensure a single instance of the connection.
- Logging for connection events and errors.
- Exception handling for connection and disconnection failures.
- Configuration management for connection parameters.
- Security management for sensitive information.

Example Usage:
```python
>>> import asyncio
>>> from milvus_api import MilvusAPI
>>> from milvus_api.connect import ConnectAPI
>>> with ConnectAPI(
>>>           alias="test_db",
>>>           user="root",
>>>           password="Milvus",
>>>           host="10.1.0.99",
>>>           port="19530",
>>>           timeout=10,
>>>           **{"db_name": "test_db"}
>>>       ) as connect_api:
>>>       pass
```
"""

import datetime
import json
from dataclasses import dataclass
from tracemalloc import Traceback
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os
import traceback
from typing import Optional, Any, Dict, Union
from pymilvus import MilvusException, MilvusClient
from pymilvus.orm import utility

from src.utils import ConfigManager, SecurityManager, async_log_decorator
from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError
from src.milvus.interfaces import IConnectAPI
from src.utils import log_decorator

# Logging setup
log = GetLogger(__name__)

@dataclass
class ConnectAPI(IConnectAPI):
    """
    Manages connections to the Milvus server using synchronous operations.

    Implements the IConnectAPI interface to handle connection establishment and disconnection.
    Uses the Singleton pattern to ensure a single connection instance.

    Attributes:
    ----------
        __instance (ConnectAPI): Singleton instance of ConnectAPI. \n
        _initialized (bool): Indicates if the connection is initialized. \n
        _alias (str): Connection alias. \n
        _timeout (float): Connection timeout in seconds. \n
        _user (str): Username for authentication. \n
        __password (str): Password for authentication. \n
        _host (str): Milvus server hostname. \n
        _port (str): Milvus server port. \n
        _uri (str): Milvus server URI. \n
        _db_name (str): Database name to connect to. \n
        __token (str): Token for authentication. \n
        _kwargs (Dict): Additional connection parameters. \n
        client (MilvusClient): The Milvus client instance. \n

    Methods:
    -------
        connect: Establishes a connection to the Milvus server. \n
        disconnect: Disconnects from the Milvus server. \n
        __enter__: Enters the context. \n
        __exit__: Exits the context. \n

    Example:
    -------
        >>> with ConnectAPI(
        >>>           alias="test_db",
        >>>           user="root",
        >>>           password="Milvus",
        >>>           host="10.1.0.99",
        >>>           port="19530",
        >>>           timeout=10,
        >>>           **{"db_name": "test_db"}
        >>>       ) as connect_api:

    Raises:
        MilvusAPIError: If connection or disconnection fails.
        MilvusValidationError: If connection parameters are invalid.
    """
    __instance: 'ConnectAPI' = None
    _initialized: bool = False
    _uri: str = "http://localhost:19530"
    _user: str = ""
    __password: str = ""
    _db_name: str = ""
    __token: str = ""
    _timeout: float = None
    _kwargs: Dict = None
    client: Optional[MilvusClient] = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures a singleton instance of ConnectAPI.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            ConnectAPI: The singleton instance.
        """
        if cls.__instance is None:
            cls.__instance = super(ConnectAPI, cls).__new__(cls)
            log.info(f"New ConnectAPI instance created @ {datetime.datetime.now()}")
        else:
            log.info(f"Using existing ConnectAPI instance created @ {datetime.datetime.now()}")
        return cls.__instance

    def __init__(
        self,
        alias: str = "default",
        uri: str = "http://localhost:19530",
        user: str = "",
        password: str = "",
        db_name: str = "",
        token: str = "",
        timeout: Optional[float] = None,
        **kwargs: Any
    ):
        """
        Initializes ConnectAPI with connection parameters.

        Args:
            alias (str): Connection alias. Defaults to "default".
            uri (str): Milvus server URI. Defaults to "http://localhost:19530".
            user (str): Username for authentication. Defaults to "".
            password (str): Password for authentication. Defaults to "".
            db_name (str): Database name. Defaults to "".
            token (str): Token for authentication. Defaults to "".
            timeout (Optional[float]): Connection timeout in seconds. Defaults to None.
            **kwargs: Additional arguments for the Milvus client.
        """
        if not hasattr(self, '_initialized') or not self._initialized:
            host_port = uri.split("//")[-1].split(":")
            self._host = host_port[0]
            self._port = int(host_port[1]) if len(host_port) > 1 else 19530
            self._alias = alias
            self._uri = uri
            self._user = user
            self.__password = password
            self._db_name = db_name
            self.__token = token
            self._timeout = timeout
            self._kwargs = kwargs
            self._initialized = False

            log.info(f"ConnectAPI initialized...")
        else:
            log.warning("ConnectAPI instance already exists. Using existing parameters.")

    def _check_and_create_database(self, db_name: str, timeout: Optional[float]) -> bool:
        """
        Checks if the specified database exists, creates it if it doesn't.

        Args:
            db_name (str): Name of the database to check/create.
            timeout (Optional[float]): Timeout for the operation.

        Returns:
            bool: True if database exists or was created successfully.

        Raises:
            MilvusAPIError: If database creation fails.
        """
        try:
            databases = self.client.list_databases(timeout=timeout)
            if db_name not in databases:
                self.client.create_database(db_name, timeout=timeout)
                log.info(f"Database {db_name} created.")
                return True
            log.debug(f"Database {db_name} already exists.")
            return True
        except MilvusException as e:
            log.error(f"Failed to check/create database {db_name}: {e}")
            raise MilvusAPIError(f"Database operation failed: {e}")

    @log_decorator
    def connect(
        self,
        alias: str = "default",
        uri: str = "http://localhost:19530",
        user: str = "",
        password: str = "",
        db_name: str = "",
        token: str = "",
        timeout: Optional[float] = None,
        **kwargs: Any
    ):
        """
        Establishes a connection to the Milvus server.

        Args:
            alias (str): Connection alias. Defaults to "default".
            uri (str): Milvus server URI. Defaults to "http://localhost:19530".
            user (str): Username for authentication. Defaults to "".
            password (str): Password for authentication. Defaults to "".
            db_name (str): Database name. Defaults to "".
            token (str): Token for authentication. Defaults to "".
            timeout (Optional[float]): Connection timeout in seconds. Defaults to None.
            **kwargs: Additional arguments for the Milvus client.
        """
        if not self._initialized:
            self._timeout = timeout
            self._connect(alias, uri, user, password, db_name, token, timeout, **kwargs)
            self._initialized = True
            if self.client is None:
                log.error("Failed to initialize Milvus client")
                raise MilvusAPIError("Milvus client is None after connection attempt")
            log.info(f"Connected to Milvus at {uri} with alias {self._db_name}")
        else:
            log.warning("Connection already initialized. Verifying client state.")
            if self.client is None:
                log.error("Client is None despite initialized state. Reconnecting.")
                self._connect(alias, uri, user, password, db_name, token, timeout, **kwargs)
                if self.client is None:
                    raise MilvusAPIError("Failed to reinitialize Milvus client")

    @log_decorator
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(MilvusException)
    )
    def _connect(
        self,
        alias: str,
        uri: str,
        user: str,
        password: str,
        db_name: str,
        token: str,
        timeout: Optional[float],
        **kwargs: Any
    ):
        """
        Internal method to connect with retry logic.
        This method is decorated with retry logic to handle connection failures.
        It will attempt to connect up to 3 times with exponential backoff.
        If the connection fails after 3 attempts, a MilvusAPIError is raised.
        This method is called by the connect method.

        It attempts to establish a connection to the Milvus server using the provided parameters,
        and create a MilvusClient instance.

        Args:
            alias (str): Connection alias.
            uri (str): Milvus server URI.
            user (str): Username for authentication.
            password (str): Password for authentication.
            db_name (str): Database name.
            token (str): Token for authentication.
            timeout (Optional[float]): Connection timeout in seconds.
            **kwargs: Additional arguments for the Milvus client.

        Raises:
            MilvusAPIError: If connection fails after retries.
        """
        try:
            log.info(f" ConnectAPI: {self}")
            self.client = MilvusClient(
                # alias=alias,
                uri=uri,
                user=user,
                password=password,
                # db_name=db_name,
                token=token,
                timeout=timeout,
                **kwargs
            )
            if db_name:
                self._check_and_create_database(db_name, timeout)
            self.client.use_database(db_name)
            log.debug(f"Connected to Milvus at {uri}, using: {self._db_name}")
        except MilvusException as e:
            log.error(f"Failed to connect: {e}")
            raise MilvusAPIError(f"Connection failed: {e}")

    @log_decorator
    def disconnect(self):
        """
        Disconnects from the Milvus server.

        Raises:
            MilvusAPIError: If disconnection fails.
        """
        try:
            if self.client is not None:
                self.client.close()
                log.info(f"Disconnected from Milvus, alias: {self._db_name}")
                self.client = None
                self._initialized = False
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")

    @log_decorator
    def __enter__(self):
        """
        Enters the context, establishing the connection.

        Returns:
            ConnectAPI: The instance of ConnectAPI.
        """
        if not self._initialized:
            self.connect(
                uri=self._uri,
                user=self._user,
                password=self.__password,
                db_name=self._db_name,
                token=self.__token,
                timeout=self._timeout,
                **self._kwargs
            )
        return self

    @log_decorator
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Traceback]):
        """
        Exits the context, disconnecting from the server.

        Args:
            exc_type (Optional[type]): The exception type, if any.
            exc_val (Optional[Exception]): The exception value, if any.
            exc_tb (Optional[Traceback]): The traceback, if any.

        Raises:
            MilvusAPIError: If disconnection fails.
        """
        try:
            if exc_type is not None:
                extracted_frames = traceback.extract_tb(exc_tb)
                formatted_traceback = "".join(traceback.format_list(extracted_frames))
                log.error(f"\nException type: {exc_type}, \nvalue: {exc_val}")
                log.error(f"Traceback: {formatted_traceback}")
            if self._initialized:
                self.disconnect()
                log.info("Disconnected from Milvus server.")
        except MilvusException as e:
            log.error(f"Failed to disconnect: {e}")
            raise MilvusAPIError(f"Disconnection failed: {e}")

    def __dict__(self) -> Dict:
        return {
            "uri": self._uri,
            "alias": self._alias,
            "user": self._user,
            "password": self.__password,
            "host": self._host,
            "port": self._port,
            "timeout": self._timeout,
            "db_name": self._db_name,
            "token": self.__token,
            "initialized": self._initialized
        }

    def to_json(self) -> str:
        return json.dumps(
            self.__dict__(),
            indent=4, sort_keys=True, default=str, check_circular=True)

    def __repr__(self):
        return f"ConnectAPI({self.__dict__()})"

    def __str__(self):
        """String representation of the AsyncMilvusClientWrapper."""
        return f"ConnectAPI({self.__dict__()})"


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

    async def _check_and_create_database(self, db_name: str, timeout: Optional[float]) -> bool:
        """
        Checks if the specified database exists, creates it if it doesn't.

        Args:
            db_name (str): Name of the database to check/create.
            timeout (Optional[float]): Timeout for the operation.

        Returns:
            bool: True if database exists or was created successfully.

        Raises:
            MilvusAPIError: If database creation fails.
        """
        try:
            databases = await utility.list_databases(using=self._alias, timeout=timeout)
            if db_name not in databases:
                await utility.create_database(db_name, using=self._alias, timeout=timeout)
                log.info(f"Database {db_name} created.")
                return True
            log.debug(f"Database {db_name} already exists.")
            return True
        except MilvusException as e:
            log.error(f"Failed to check/create database {db_name}: {e}")
            raise MilvusAPIError(f"Database operation failed: {e}")

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
        if self._initialized and self._db_name:
            await self._check_and_create_database(self._db_name, self._timeout)
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

    def __dict__(self) -> Dict:
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

    def to_json(self) -> str:
        return json.dumps(
            self.__dict__(),
            indent=4, sort_keys=True, default=str, check_circular=True)

    def __repr__(self):
        return f"AsyncMilvusClientWrapper({self.__dict__()})"

    def __str__(self):
        """String representation of the AsyncMilvusClientWrapper."""
        return f"AsyncMilvusClientWrapper({self.__dict__()})"

