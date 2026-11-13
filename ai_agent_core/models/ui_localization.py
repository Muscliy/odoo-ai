"""Localize template display text while preserving rule and integration keys."""

from collections.abc import Callable


def localize_template(value: object, translate: Callable[[str], str], *, text: bool = False) -> object:
    if isinstance(value, dict):
        return {
            key: localize_template(
                item, translate,
                text=key in {"name", "description", "mission", "values", "goals", "question", "options"},
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [localize_template(item, translate, text=text) for item in value]
    if text and isinstance(value, str):
        return translate(value)
    return value
