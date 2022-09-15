class ConfigurationError(Exception):
    '''
    Raised when a problem occurs with the configuration of the library.
    '''
    pass


class APIError(Exception):
    '''
    Raised when a problem occurs in the API functions.
    '''
    pass


class ChunkedUploadError(Exception):
    '''
    Raised when an error occurs processing a chunked upload.
    '''
    pass
