from src.milvus.interfaces import IState
from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)

class LoadedState(IState):
    """
    State for loaded collections.

    Implements the IState interface to handle behavior for loaded collections.

    Methods:
        handle: Handles the loaded state behavior.

    Example:
        ```python
        state = LoadedState()
        state.handle(context)
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
