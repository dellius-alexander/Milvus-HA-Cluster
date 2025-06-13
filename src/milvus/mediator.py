from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)


class Mediator:
    """Mediator for collection communication.

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
        """Notifies the mediator of an event.

        Args:
            sender: The sender of the event.
            event: The event details.

        """
        log.info(f"Mediator notified by {sender} of {event}")
