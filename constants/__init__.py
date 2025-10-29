from enum import IntEnum



class ResponseCode(IntEnum):
    SUCCESS = 0
    FAIL = -1
    AUTH_FAILED = -2
    UPLOAD_FAILED = -3

    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500

def load_args():
    import constants.browser
    import constants.frp