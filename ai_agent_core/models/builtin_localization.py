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
    """Translate stock skill fields, preserving each independently edited field."""
    return localize_seed_records(env, "builtin_skills_zh.json")


def skill_display_labels(env, records=None) -> dict[int, str]:
    """Keep slash-command names stable while showing Chinese skill titles."""
    if not (env.lang or "").startswith("zh"):
        return {}
    path = Path(__file__).resolve().parents[1] / "data/builtin_skills_zh.json"
    labels = {}
    selected = {record.id: record for record in records} if records is not None else None
    for definition in json.loads(path.read_text(encoding="utf-8")):
        record = env.ref(definition["xmlid"], raise_if_not_found=False)
        if selected is not None:
            record = selected.get(record.id) if record else None
        names = {definition["technical_name"]}
        if "name" in definition["fields"]:
            names.add(definition["fields"]["name"]["value"])
        if record and record.exists() and record.name in names:
            labels[record.id] = definition["label"]
    return labels


def localize_seed_records(env, filename: str) -> list[int]:
    """Apply reviewed translations only when the source fingerprint matches."""
    path = Path(__file__).resolve().parents[1] / "data" / filename
    changed = []
    for definition in json.loads(path.read_text(encoding="utf-8")):
        record = env.ref(definition["xmlid"], raise_if_not_found=False)
        if not record or not record.exists():
            continue
        values = {}
        for field, translation in definition["fields"].items():
            current = record[field] or ""
            digest = hashlib.sha256(current.encode()).hexdigest()
            if digest == translation["source_sha256"] and current != translation["value"]:
                values[field] = translation["value"]
        if values:
            record.with_context(tracking_disable=True, mail_notrack=True).write(values)
            changed.append(record.id)
    return changed


def localize_tool_descriptions(env) -> list[int]:
    """Use builtin_name so renamed tools retain their configuration and links."""
    path = Path(__file__).resolve().parents[1] / "data/builtin_tools_zh.json"
    changed = []
    for definition in json.loads(path.read_text(encoding="utf-8")):
        for record in env["ai.tool"].search([("builtin_name", "=", definition["builtin_name"])]):
            values = {}
            for field, translation in definition["fields"].items():
                current = record[field] or ""
                if hashlib.sha256(current.encode()).hexdigest() == translation["source_sha256"]:
                    values[field] = translation["value"]
            if values:
                record.with_context(tracking_disable=True, mail_notrack=True).write(values)
                changed.append(record.id)
    return changed


def localize_runtime_defaults(env) -> None:
    """Replace exact old defaults; retain user-authored system instructions."""
    path = Path(__file__).resolve().parents[1] / "data/builtin_defaults_zh.json"
    for definition in json.loads(path.read_text(encoding="utf-8")):
        records = env[definition["model"]].search([
            (definition["field"], "=", definition["source"]),
        ])
        records.with_context(tracking_disable=True, mail_notrack=True).write({
            definition["field"]: definition["value"],
        })
