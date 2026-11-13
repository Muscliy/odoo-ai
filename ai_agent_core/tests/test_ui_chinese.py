"""Database-free behavior checks for dynamic UI text and template option values.

Run: python -m unittest discover -s ai_agent_core/tests -p test_ui_chinese.py
"""

import ast
import hashlib
import importlib.util
import json
import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import polib
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("AI_I18N_SOURCE_ROOT", ROOT))
CATALOG = {entry.msgid: entry.msgstr for entry in polib.pofile(str(ROOT / "i18n/zh_CN.po"))}


def method(relative_path, class_name, name):
    path = SOURCE_ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    function = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == name)
    function.decorator_list = []
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class Environment:
    def __init__(self, lang="zh_CN"):
        self.lang = lang

    def _(self, source, *args, **kwargs):
        translated = CATALOG.get(source, source) if self.lang == "zh_CN" else source
        return translated % (kwargs or args) if args or kwargs else translated


class Records(list):
    def __init__(self, records, lang="zh_CN"):
        super().__init__(records)
        self.env = Environment(lang)


class TestDynamicChinese(unittest.TestCase):
    def test_builtin_localization_is_idempotent_and_keeps_custom_descriptions(self):
        spec = importlib.util.spec_from_file_location("builtin_localization", ROOT / "models/builtin_localization.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        definition = {
            "legacy_name": "Legacy Builder", "xmlid": "ai_agent_core.coworker_test",
            "name": "配置助手", "description": "中文说明", "sub_description": "中文用途",
            "source_description_sha256": hashlib.sha256(b"Default description").hexdigest(),
        }
        record = MagicMock()
        record.id, record.name, record.description, record.sub_description = 7, "Legacy Builder", "Default description", ""
        record.with_context.return_value = record
        record.__getitem__.side_effect = lambda key: getattr(record, key)
        record.write.side_effect = lambda values: [setattr(record, key, value) for key, value in values.items()]
        env = MagicMock()
        env.ref.return_value = record
        with patch.object(module, "builtin_definitions", return_value=[definition]):
            self.assertEqual(module.localize_builtin_coworkers(env), [7])
            self.assertEqual(record.description, "中文说明")
            self.assertEqual(module.localize_builtin_coworkers(env), [])
            record.description = "用户自己写的业务要求"
            self.assertEqual(module.localize_builtin_coworkers(env), [])
            self.assertEqual(record.description, "用户自己写的业务要求")

    def test_python_translation_markers_can_be_loaded_by_odoo(self):
        catalog = polib.pofile(str(ROOT / "i18n/zh_CN.po"))
        for path in list((ROOT / "models").glob("*.py")) + list((ROOT / "wizards").glob("*.py")):
            for node in ast.walk(ast.parse(path.read_text())):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "_" and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str) and node.args[0].value):
                    continue
                source = node.args[0].value
                entry = catalog.find(source)
                with self.subTest(path=path.name, source=source[:60]):
                    self.assertIsNotNone(entry)
                    self.assertIn("odoo-python", entry.comment)
                    self.assertTrue(any(key.startswith("code:") for key, _ in entry.occurrences))

    def test_all_six_orchestration_explanations_are_chinese(self):
        compute = method("models/ai_coworker.py", "AICoworker", "_compute_orchestration_mode_help")
        records = Records([SimpleNamespace(orchestration_mode=mode) for mode in (
            "single", "supervisor", "buzz", "linear", "conference", "automation",
        )])
        compute(records)
        for record in records:
            with self.subTest(mode=record.orchestration_mode):
                self.assertRegex(record.orchestration_mode_help, r"[\u4e00-\u9fff]")
                self.assertNotIn("agent", record.orchestration_mode_help)

    def manual_instructions(self, lang):
        compute = method("models/ai_coworker.py", "AICoworker", "_compute_manual_call_instructions")
        record = SimpleNamespace(id=42, name="测试 <助手>", get_external_id=lambda: {})
        compute(Records([record], lang))
        return record.manual_call_instructions

    def test_manual_instructions_and_examples_are_chinese(self):
        instructions = self.manual_instructions("zh_CN")
        self.assertIn("通过代码调用", instructions)
        self.assertIn("示例 1", instructions)
        self.assertIn("请在此填写要处理的问题", instructions)
        self.assertNotIn("Your question", instructions)
        self.assertNotIn("Alternative call path", instructions)

    def test_translated_example_preserves_executable_code_and_routes(self):
        instructions = self.manual_instructions("zh_CN")
        document = etree.HTML(instructions)
        code = document.xpath("//pre/code")[0].text
        ast.parse(code)
        self.assertIn('env["ai.coworker.session"]', code)
        self.assertIn('"status": "active"', code)
        self.assertIn("POST /ai/webhook/42", instructions)
        self.assertIn("Authorization: Bearer", instructions)
        self.assertIn("&lt;助手&gt;", instructions)

    def test_english_language_remains_available(self):
        self.assertIn("Call 测试", self.manual_instructions("en_US"))
        self.assertIn("Your question here", self.manual_instructions("en_US"))

    def test_onboarding_displays_chinese_questions_and_options(self):
        get_questions = method("models/ai_onboarding.py", "AIOnboarding", "_get_interview_questions")
        source = json.loads((ROOT / "data/templates/accounting_firm.json").read_text())
        record = SimpleNamespace(env=Environment(), template_id=SimpleNamespace(structure_json=source), detected_modules={"account": {}})
        questions = get_questions(record)
        self.assertEqual(questions[0]["id"], "account_moms")
        self.assertEqual(questions[0]["question"], "是否为客户办理增值税申报？")
        self.assertEqual(questions[0]["options"], ["是", "否"])

    def test_chinese_answer_keeps_original_proposal_rule_key(self):
        answer = method("models/ai_onboarding.py", "AIOnboarding", "action_answer")
        source = json.loads((ROOT / "data/templates/accounting_firm.json").read_text())
        values = {}
        record = SimpleNamespace(env=Environment(), template_id=SimpleNamespace(structure_json=source), answers={},
                                 ensure_one=lambda: None, write=values.update, _get_interview_questions=lambda: [])
        answer(record, "account_moms", "是")
        self.assertEqual(values["answers"], {"account_moms": "Ja"})
        self.assertIn(values["answers"]["account_moms"], source["proposal_generator"]["account_moms"])

    def test_free_text_answer_is_preserved(self):
        answer = method("models/ai_onboarding.py", "AIOnboarding", "action_answer")
        values = {}
        record = SimpleNamespace(env=Environment(), template_id=False, answers={}, ensure_one=lambda: None,
                                 write=values.update, _get_interview_questions=lambda: [])
        answer(record, "custom", "请优先处理客户报价")
        self.assertEqual(values["answers"]["custom"], "请优先处理客户报价")

    def test_template_translation_keeps_machine_values_and_rule_keys(self):
        spec = importlib.util.spec_from_file_location("ui_localization", ROOT / "models/ui_localization.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = json.loads((ROOT / "data/templates/accounting_firm.json").read_text())
        localized = module.localize_template(source, Environment()._)
        self.assertEqual(localized["name"], "财务与审计服务公司")
        self.assertEqual(localized["industry"], source["industry"])
        self.assertIn("Ja", localized["proposal_generator"]["account_moms"])
        coworker = localized["proposal_generator"]["account_moms"]["Ja"]["coworkers"][0]
        self.assertEqual(coworker["name"], "增值税助手")
        self.assertEqual(coworker["agent"]["tools"], ["account_read"])
        self.assertEqual(coworker["mode"], "single")

    def test_seed_template_visible_text_has_chinese_translation(self):
        def check(value, text=False):
            if isinstance(value, dict):
                for key, item in value.items():
                    check(item, key in {"name", "description", "question", "options", "goals"})
            elif isinstance(value, list):
                for item in value:
                    check(item, text)
            elif text and isinstance(value, str) and re.search(r"[A-Za-zÅÄÖåäö]", value):
                with self.subTest(text=value):
                    self.assertRegex(CATALOG.get(value, ""), r"[\u4e00-\u9fff]")
        for path in (ROOT / "data/templates").glob("*.json"):
            check(json.loads(path.read_text()))

    def test_builtin_coworkers_have_clear_chinese_names_and_descriptions(self):
        definitions = json.loads((ROOT / "data/builtin_coworkers_zh.json").read_text())
        self.assertEqual(len(definitions), 5)
        for definition in definitions:
            with self.subTest(name=definition["legacy_name"]):
                for field in ("name", "sub_description", "description"):
                    self.assertRegex(definition[field], r"[\u4e00-\u9fff]")
                self.assertNotIn("You are", definition["description"])
                self.assertNotIn("Du är", definition["description"])
        builder = next(item for item in definitions if item["legacy_name"] == "Quest Builder")
        for tool in ("inventory_architecture", "inventory_skills", "inventory_agents", "inventory_models",
                     "inventory_tools", "inventory_identities", "inventory_quests", "read_skill"):
            self.assertIn(tool + "(", builder["description"])
        self.assertIn("未得到用户明确批准", builder["description"])

    def test_seed_skill_descriptions_are_chinese_and_keep_identifiers(self):
        definitions = json.loads((ROOT / "data/builtin_skill_descriptions_zh.json").read_text())
        self.assertEqual(len(definitions), 20)
        for definition in definitions:
            with self.subTest(name=definition["name"]):
                self.assertRegex(definition["description"], r"[\u4e00-\u9fff]")
                self.assertTrue(definition["xmlid"].startswith("ai_agent_core."))
                self.assertEqual(len(definition["source_description_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
