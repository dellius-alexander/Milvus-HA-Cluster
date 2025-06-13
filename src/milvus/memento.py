

class Memento:
    """Memento for saving state.

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

