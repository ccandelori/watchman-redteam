from __future__ import annotations

from pydantic import ValidationError
from pydantic_core import ErrorDetails


def format_validation_error_details(exc: ValidationError) -> str:
    details = [_format_validation_detail(error) for error in exc.errors(include_input=False)]
    return "; ".join(details)


def _format_validation_detail(error: ErrorDetails) -> str:
    location = ".".join(str(part) for part in error["loc"])
    message = str(error["msg"])
    error_type = str(error["type"])
    if location == "":
        return f"{message} [{error_type}]"
    return f"{location}: {message} [{error_type}]"
