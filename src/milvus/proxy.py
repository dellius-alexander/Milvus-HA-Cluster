from src.milvus.exceptions import MilvusAPIError
from src.utils import SecurityManager


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
        proxy.request()
        ```

    Raises:
        MilvusAPIError: If authorization or request fails.
    """

    def __init__(self, real_subject, security: SecurityManager):
        self.real_subject = real_subject
        self.security = security

    def request(self, *args, **kwargs):
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
            return self.real_subject.request(*args, **kwargs)
        raise MilvusAPIError("Unauthorized")

