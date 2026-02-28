class StorageError(Exception):
    pass


class FileTooLargeError(StorageError):
    pass


class StorageFileNotFoundError(StorageError):
    pass
