"""Chinese built-in coworkers, addressed by stable IDs instead of UI names."""

import hashlib
import json
from pathlib import Path


def builtin_definitions() -> list[dict[str, str]]:
    path = Path(__file__).resolve().parents[1] / "data/builtin_coworkers_zh.json"
    return json.loads(path.read_text(encoding="utf-8"))


def find_builtin(env, legacy_name: str):
    definition = next(item for item in builtin_definitions() if item["legacy_name"] == legacy_name)
    record = env.ref(definition["xmlid"], raise_if_not_found=False)
    if record and record.exists():
        return record
    return env["ai.coworker"].search([
        ("name", "in", [legacy_name, definition["name"]]),
    ], limit=1)


def localize_builtin_coworkers(env, *, overwrite: bool = False) -> list[int]:
    """Update known defaults only; keep edited descriptions unless requested."""
    changed = []
    for definition in builtin_definitions():
        record = find_builtin(env, definition["legacy_name"])
        if not record:
            continue
        digest = hashlib.sha256((record.description or "").encode()).hexdigest()
        values = {}
        if overwrite or record.name == definition["legacy_name"]:
            values["name"] = definition["name"]
        if overwrite or digest == definition["source_description_sha256"]:
            values.update({key: definition[key] for key in ("description", "sub_description")})
        values = {key: value for key, value in values.items() if record[key] != value}
        if values:
            record.with_context(tracking_disable=True, mail_notrack=True).write(values)
            changed.append(record.id)
        module, name = definition["xmlid"].split(".", 1)
        if not env.ref(definition["xmlid"], raise_if_not_found=False):
            env["ir.model.data"].sudo().create({
                "module": module, "name": name, "model": "ai.coworker",
                "res_id": record.id, "noupdate": True,
            })
    return changed


def localize_skill_descriptions(env) -> list[int]:
    """Translate stock descriptions without renaming slash-command identifiers."""
    path = Path(__file__).resolve().parents[1] / "data/builtin_skill_descriptions_zh.json"
    changed = []
    for definition in json.loads(path.read_text(encoding="utf-8")):
        record = env.ref(definition["xmlid"], raise_if_not_found=False)
        if not record or not record.exists():
            continue
        digest = hashlib.sha256((record.description or "").encode()).hexdigest()
        if digest == definition["source_description_sha256"]:
            record.with_context(tracking_disable=True, mail_notrack=True).write({
                "description": definition["description"],
            })
            changed.append(record.id)
    return changed
