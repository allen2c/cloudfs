"""CloudFS exceptions."""


class CloudOperationError(NotImplementedError):
    """Raised when a pathlib.Path operation has no meaningful equivalent for cloud storage."""
