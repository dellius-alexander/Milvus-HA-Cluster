
from pymilvus import MilvusException

from src.logger import getLogger as GetLogger
from src.milvus.exceptions import MilvusAPIError, MilvusValidationError
from src.milvus.interfaces import IAdminAPI, IConnectAPI
from src.utils import async_log_decorator

# Logging setup
log = GetLogger(__name__)

class AdminAPI(IAdminAPI):
    """Manages administrative tasks in Milvus, such as user management.

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
        api.create_user("new_user", "password")
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
    def create_user(self, username: str, password: str):
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
            self._connect_api.client.create_user(username, password)
            log.info(f"Created user {username}")
        except MilvusException as e:
            log.error(f"Failed to create user: {e}")
            raise MilvusAPIError(f"User creation failed: {e}")

    @async_log_decorator
    def list_users(self) -> list[str]:
        """Lists all users in Milvus.

        Returns:
            List[str]: List of usernames.

        Raises:
            MilvusAPIError: If listing fails.

        """
        try:
            users = self._connect_api.client.list_users()
            log.info(f"Listed {len(users)} users")
            return users
        except MilvusException as e:
            log.error(f"Failed to list users: {e}")
            raise MilvusAPIError(f"List users failed: {e}")


