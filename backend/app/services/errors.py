class ServiceError(Exception):
    pass


class AuthFailedError(ServiceError):
    pass


class FileNotFoundError(ServiceError):
    pass


class ShareLinkNotFoundError(ServiceError):
    pass


class ShareLinkInactiveError(ServiceError):
    pass


class ShareLinkExpiredError(ServiceError):
    pass


class SharePasswordInvalidError(ServiceError):
    pass


class ShareDownloadLimitReachedError(ServiceError):
    pass
