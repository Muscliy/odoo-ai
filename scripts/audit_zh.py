"""Audit user-facing translation candidates in every Vertel AI module.

Run from the Odoo root:
python -m external_addons.vertel_ai.scripts.audit_zh --output report.json
Technical values are excluded by syntactic context, not by language guessing.
"""
import argparse
import hashlib
import ast
import json
import re
from pathlib import Path
from lxml import etree as ElementTree
from odoo.tools.translate import xml_translate

import polib

ROOT = Path(__file__).resolve().parents[1]
UI_ATTRIBUTES = {"string", "help", "placeholder", "title", "alt", "confirm"}
DATA_FIELDS = {"description", "ai_role", "ai_goal", "ai_backstory", "sub_description",
               "recipe_text", "trigger_keywords", "improvement_guidance"}


def has_text(value):
    return bool(value and re.search(r"[A-Za-zÅÄÖåäö]", value))


def python_labels(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeError):
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "description"
                        and isinstance(value, ast.Constant) and isinstance(value.value, str)
                        and has_text(value.value)):
                    yield getattr(value, "lineno", 0), value.value, "raw-description"
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        values = []
        if name == "Tool":
            values.extend(k.value for k in node.keywords if k.arg == "description")
        if name in {"_", "_t", "_lt", "UserError", "ValidationError", "AccessError"}:
            values.extend(node.args[:1])
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "fields":
            # Many2one/Many2many first positional argument is the model, not a label.
            start = {"Many2one": 1, "One2many": 2, "Many2many": 4}.get(name, 0)
            if name in {"Char", "Text", "Html", "Boolean", "Integer", "Float", "Monetary", "Date", "Datetime", "Binary", "Image", "Many2one", "Many2many", "One2many", "Reference", "Json"}:
                values.extend(node.args[start:start + 1])
            elif node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
                for pair in node.args[0].elts:
                    if isinstance(pair, (ast.Tuple, ast.List)) and len(pair.elts) == 2:
                        values.append(pair.elts[1])
        values.extend(k.value for k in node.keywords if k.arg in {"string", "help"})
        for value in values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str) and has_text(value.value):
                yield node.lineno, value.value, "python"


def xml_labels(path):
    try:
        root = ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, UnicodeError):
        return
    for node in root.xpath('//field[@name="arch"]|//template|//templates'):
        arch = ''.join(ElementTree.tostring(child, encoding="unicode") for child in node) if node.tag == "field" else ElementTree.tostring(node, encoding="unicode")
        terms = []
        xml_translate(lambda term: terms.append(term) or term, arch)
        for term in terms:
            if has_text(term):
                yield 0, term, "xml"
    for record in root.iter("record"):
        for field in record.findall("field"):
            if field.get("name") in DATA_FIELDS and has_text(field.text):
                yield 0, field.text, "seed:" + (record.get("id") or "") + ":" + field.get("name")


def scan(root=ROOT):
    results = []
    for manifest in sorted(root.glob("*/__manifest__.py")):
        module = manifest.parent
        try:
            installable = ast.literal_eval(manifest.read_text()).get("installable", True)
        except (ValueError, SyntaxError):
            installable = False
        catalog_path = module / "i18n/zh_CN.po"
        catalog = {e.msgid: e.msgstr for e in polib.pofile(str(catalog_path))} if catalog_path.exists() else {}
        localized = {}
        for name in ("builtin_skills_zh.json", "builtin_records_zh.json"):
            path = module / "data" / name
            if path.exists():
                for entry in json.loads(path.read_text()):
                    for key, value in entry["fields"].items():
                        localized[(entry["xmlid"].split(".", 1)[1], key)] = value["source_sha256"]
        for path in sorted(module.rglob("*")):
            if not path.is_file() or any(p in {"tests", "test", "demo", "migrations", "__pycache__", "node_modules", ".git"} for p in path.parts):
                continue
            if path.name in {"__manifest__.py", "__init__.py"}:
                continue
            labels = python_labels(path) if path.suffix == ".py" else xml_labels(path) if path.suffix == ".xml" else ()
            for line, source, kind in labels:
                covered = bool(catalog.get(source)) or bool(re.search(r"[\u4e00-\u9fff]", source))
                if kind.startswith("seed:"):
                    _, record, field = kind.split(":", 2)
                    covered = covered or localized.get((record, field)) == hashlib.sha256(source.encode()).hexdigest()
                results.append({"module": module.name, "installable": installable,
                                "path": str(path.relative_to(root)), "line": line,
                                "kind": kind, "source": source, "covered": covered})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = scan()
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    modules = sorted({row["module"] for row in rows})
    for module in modules:
        group = [row for row in rows if row["module"] == module]
        print(f'{module}: {len(group)} candidates, {sum(not row["covered"] for row in group)} need review')
