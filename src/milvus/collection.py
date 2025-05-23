from typing import List, Union, Dict, Any

from pymilvus import Collection, DataType, FieldSchema, CollectionSchema, MilvusException

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusValidationError, MilvusAPIError
from src.milvus.interfaces import IConnectAPI, ICollectionAPI
from src.utils import async_log_decorator, log_decorator

# Logging setup
log = GetLogger(__name__)

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
        api.create_collection("test_collection", fields, "test_db")
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
    @log_decorator
    def _build_collection_schema(self,
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
        # Validate connection
        if self._connect_api.client is None:
            log.error("No valid Milvus client connection")
            raise MilvusAPIError("Cannot create collection: No valid Milvus client connection")

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
            collection_schema = schema or self._build_collection_schema(
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
            self._connect_api.client.create_collection(
                collection_name=collection_name,
                schema=collection_schema,
                **create_kwargs
            )

            log.info(f"Created collection: {collection_name}, Database: {database_name}")

            # Instantiate the collection object
            collection = Collection(
                name=collection_name,
                schema=collection_schema,
                using=self._connect_api._alias,
                **{"collection.ttl.seconds": 1800}
            )
            log.info(f"Instantiate collection: {collection_name}, Database: {database_name}")

            # Create index if specified
            if index_params is not None:
                vector_fields = [f.name for f in collection_schema.fields if
                                 f.dtype in {DataType.FLOAT_VECTOR, DataType.BINARY_VECTOR}]
                if vector_field_name not in vector_fields:
                    raise MilvusValidationError(f"Vector field {vector_field_name} not found in schema")
                index_params = dict(index_params)  # Copy to avoid modifying input
                if "metric_type" not in index_params:
                    index_params["metric_type"] = metric_type
                status = await collection.create_index(
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
    def list_collections(self, database_name: str = "default") -> List[str]:
        """Lists all collections in the specified database.

        Args:
            database_name (str): Database name. Defaults to "default".

        Returns:
            List[str]: List of collection names.

        Raises:
            MilvusAPIError: If listing fails.
        """
        try:
            collections = self._connect_api.client.list_collections(db_name=database_name)
            log.info(f"Listed {len(collections)} collections in database {database_name}")
            return collections
        except MilvusException as e:
            log.error(f"Failed to list collections: {e}")
            raise MilvusAPIError(f"List collections failed: {e}")

    @async_log_decorator
    def describe_collection(self, collection_name: str, database_name: str = "default") -> Dict[str, Any]:
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
            desc = self._connect_api.client.describe_collection(
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
            await self._connect_api.client.drop_collection(
                collection_name=collection_name,
                timeout= timeout
            )
            log.info(f"Dropped collection {collection_name} from database {timeout}")
            return {"message": f"Collection {collection_name} dropped", "status": "success"}
        except MilvusException as e:
            log.error(f"Failed to drop collection: {e}")
            raise MilvusAPIError(f"Drop collection failed: {e}")

