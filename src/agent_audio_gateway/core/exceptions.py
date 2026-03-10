class GatewayError(Exception):
    exit_code: int = 6
    retryable: bool = False

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class InputError(GatewayError):
    exit_code = 3


class PreprocessingError(GatewayError):
    exit_code = 4


class SegmentationError(GatewayError):
    exit_code = 4


class ModelError(GatewayError):
    exit_code = 5


class AggregationError(GatewayError):
    exit_code = 4


class ConfigError(GatewayError):
    exit_code = 6
