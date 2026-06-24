from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError
from yaml.error import MarkedYAMLError, YAMLError

from aegis_redteam.validation_errors import format_validation_error_details

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_yaml_model(path: Path | str, model_type: type[ModelT], model_name: str) -> ModelT:
    yaml_path = Path(path)
    try:
        raw_text = yaml_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {yaml_path}") from exc

    try:
        payload: object = yaml.safe_load(raw_text)
    except YAMLError as exc:
        raise ValueError(_format_yaml_error(yaml_path, exc)) from exc

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(yaml_path, model_name, exc)) from exc


def _format_yaml_error(path: Path, exc: YAMLError) -> str:
    if isinstance(exc, MarkedYAMLError):
        mark = exc.context_mark if exc.context_mark is not None else exc.problem_mark
        if mark is not None:
            detail = exc.problem if exc.problem is not None else str(exc)
            return f"{path}:{mark.line + 1}:{mark.column + 1}: invalid YAML: {detail}"
    return f"{path}: invalid YAML: {exc}"


def _format_validation_error(path: Path, model_name: str, exc: ValidationError) -> str:
    return f"{path}: invalid {model_name}: {format_validation_error_details(exc)}"
