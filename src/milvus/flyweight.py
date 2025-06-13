

class FlyweightFactory:
    """Flyweight for sharing common data.

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
        """Retrieves or creates a flyweight object.

        Args:
            key: The key identifying the flyweight.

        Returns:
            object: The flyweight object.

        """
        if key not in cls._flyweights:
            cls._flyweights[key] = object()
        return cls._flyweights[key]

