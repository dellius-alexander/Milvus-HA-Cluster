from pymilvus import FieldSchema, DataType, Collection

from src.logger import getLogger as GetLogger
from src.milvus.collection import CollectionAPI
from src.milvus.connect import ConnectAPI

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
        collection = factory.create_standard_collection("test_collection", 128, "test_db")
        ```

    Raises:
        MilvusValidationError: If input parameters are invalid.
        MilvusAPIError: If collection creation fails.
    """

    @staticmethod
    def create_standard_collection(collection_name: str, dimension: int, db_name: str) -> Collection:
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
        return CollectionAPI(ConnectAPI()).create_collection(collection_name, fields, db_name)
