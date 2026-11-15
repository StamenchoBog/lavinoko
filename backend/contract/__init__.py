"""The data contract between the backend and the page. See models.py."""

from __future__ import annotations

import json

from pydantic import ValidationError

from contract.models import Model


class ContractError(ValueError):
    """Output that does not match the data contract. It must not be published."""


def checked_json(model: type[Model], data: object, **dumps_kwargs) -> str:
    """`data` as JSON text, after checking that the text matches `model`."""
    text = json.dumps(data, ensure_ascii=False, **dumps_kwargs)
    try:
        model.model_validate_json(text)
    except ValidationError as e:
        raise ContractError(f"{model.__name__} does not match the contract:\n{e}") from e
    return text
