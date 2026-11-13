"""Database-free checks for Chinese seed upgrades and tool selection."""
import ast
import asyncio
import hashlib
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOCALIZATION = load_module("builtin_zh_localization", ROOT / "models/builtin_localization.py")
SELECTOR = load_module("builtin_zh_selector", ROOT / "core/tool_select.py")


class Record(dict):
    def __init__(self, number, values):
        super().__init__(values)
        self.id = number
        self.name = values.get("name", "")
        self.writes = []

    def exists(self):
        return True

    def with_context(self, **kwargs):
        return self

    def write(self, values):
        self.update(values)
        self.name = self.get("name", "")
        self.writes.append(values)


class Environment:
    lang = "zh_CN"

    def __init__(self, records):
        self.records = records

    def ref(self, xmlid, **kwargs):
        return self.records.get(xmlid)

    def __getitem__(self, model):
        return SimpleNamespace(search=lambda domain: [record for record in self.records.values()
                               if record.get("builtin_name") == domain[0][2]])


def builtin_tools():
    tree = ast.parse((ROOT / "core/tools.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "builtin_tools")
    tools = []
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Tool":
            values = {keyword.arg: keyword.value for keyword in node.keywords}
            tools.append(SimpleNamespace(**{
                key: ast.literal_eval(value) for key, value in values.items()
                if key in {"name", "description", "parameters", "risk_level"}
            }))
    return tools


class TestBuiltinChinese(unittest.TestCase):
    def test_all_twenty_skills_have_chinese_source_content_and_triggers(self):
        definitions = json.loads((ROOT / "data/builtin_skills_zh.json").read_text())
        records = {}
        for path in (ROOT / "data").glob("*.xml"):
            for record in etree.parse(str(path)).xpath('//record[@model="ai.skill"]'):
                records["ai_agent_core." + record.get("id")] = {
                    field.get("name"): field.text for field in record.findall("field")
                }
        self.assertEqual(len(definitions), 20)
        for definition in definitions:
            for name, translation in definition["fields"].items():
                with self.subTest(skill=definition["xmlid"], field=name):
                    self.assertEqual(records[definition["xmlid"]][name], translation["value"])
                    self.assertRegex(translation["value"], r"[\u4e00-\u9fff]")
            self.assertIn("trigger_keywords", definition["fields"])
            self.assertNotRegex(definition["fields"]["trigger_keywords"]["value"], r"[åäöÅÄÖ]")
        body = records["ai_agent_core.skill_orchestration_supervisor"]["recipe_text"]
        for placeholder in ("{agents}", "{min_confidence}", "{max_iterations}"):
            self.assertIn(placeholder, body)

    def test_upgrade_preserves_custom_fields_and_is_idempotent(self):
        record = Record(1, {"name": "Mail: Hitta/skapa res.partner",
                            "description": "用户自己的说明", "recipe_text": "用户自己的操作流程",
                            "trigger_keywords": ""})
        env = Environment({"ai_agent_core.skill_mail_partner": record})
        self.assertEqual(LOCALIZATION.localize_skill_descriptions(env), [1])
        self.assertEqual(record["description"], "用户自己的说明")
        self.assertEqual(record["recipe_text"], "用户自己的操作流程")
        self.assertEqual(record["name"], "邮件：查找或创建联系人")
        self.assertIn("邮件", record["trigger_keywords"])
        self.assertEqual(LOCALIZATION.localize_skill_descriptions(env), [])

    def test_display_label_keeps_slash_name_and_custom_names(self):
        record = Record(1, {"name": "odoo-core"})
        env = Environment({"ai_agent_core.skill_odoo_core": record})
        self.assertEqual(LOCALIZATION.skill_display_labels(env), {1: "Odoo 核心业务操作"})
        self.assertEqual(record["name"], "odoo-core")
        record.name = "用户自定义名字"
        self.assertEqual(LOCALIZATION.skill_display_labels(env), {})

    def test_display_label_does_not_read_other_skills(self):
        class RestrictedSkill:
            id = 2

            @property
            def name(self):
                raise PermissionError("another skill is private")

        record = Record(1, {"name": "odoo-core"})
        env = Environment({"ai_agent_core.skill_odoo_core": record,
                           "ai_agent_core.skill_mail_partner": RestrictedSkill()})
        self.assertEqual(LOCALIZATION.skill_display_labels(env, [record]),
                         {1: "Odoo 核心业务操作"})

    def test_renamed_tool_is_localized_by_builtin_identity(self):
        definition = next(item for item in json.loads((ROOT / "data/builtin_tools_zh.json").read_text())
                          if item["builtin_name"] == "odoo_search")
        record = Record(7, {"name": "TYJ_search", "builtin_name": "odoo_search",
                            "description": "custom", "parameters": "custom schema"})
        env = Environment({"tool": record})
        self.assertEqual(LOCALIZATION.localize_tool_descriptions(env), [])
        source = "Search records via the ORM (search_read) with Odoo domain syntax. Returns id/name/display_name/create_date by default; pass fields to get more. Limit defaults to 20."
        record["description"] = source
        self.assertEqual(LOCALIZATION.localize_tool_descriptions(env), [7])
        self.assertEqual(record["name"], "TYJ_search")
        self.assertEqual(record["parameters"], "custom schema")
        self.assertEqual(record["description"], definition["fields"]["description"]["value"])
        self.assertEqual(LOCALIZATION.localize_tool_descriptions(env), [])

    def test_tool_parameter_contracts_and_approval_levels_are_unchanged(self):
        expected = json.loads((ROOT / "tests/fixtures/builtin_tool_contracts.json").read_text())

        def strip(value):
            if isinstance(value, dict):
                return {key: strip(item) for key, item in value.items() if key != "description"}
            if isinstance(value, list):
                return [strip(item) for item in value]
            return value

        tools = builtin_tools()
        self.assertEqual({tool.name for tool in tools}, set(expected))
        for tool in tools:
            self.assertRegex(tool.description, r"[\u4e00-\u9fff]")
            contract = {"parameters": strip(tool.parameters), "risk_level": getattr(tool, "risk_level", None)}
            digest = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest, expected[tool.name], tool.name)

    def test_chinese_employee_queries_select_odoo_search(self):
        tools = builtin_tools()
        selector = SELECTOR.LexicalSelector(tools)
        for prompt in ("查询员工信息", "查询销售部员工的岗位", "查询联系人邮箱"):
            selected = max(tools, key=lambda tool: selector.score(prompt, tool))
            self.assertEqual(selected.name, "odoo_search", prompt)
        selected = max(tools, key=lambda tool: selector.score("删除员工记录", tool))
        self.assertEqual(selected.name, "odoo_unlink")

    def test_embedded_tool_errors_are_chinese_and_keep_recovery_metadata(self):
        document = etree.parse(str(ROOT / "data/youtube_tools.xml"))
        code = document.xpath('//record[@id="tool_youtube_get_transcript"]/field[@name="code"]')[0].text
        namespace = {}
        exec(compile(code, "youtube_transcript_tool", "exec"), namespace)
        stub = SimpleNamespace(YouTubeTranscriptApi=object)
        with patch.dict(sys.modules, {"youtube_transcript_api": stub}):
            result = json.loads(asyncio.run(namespace["execute"]()))
        self.assertIn("缺少必填参数", result["error"])
        self.assertEqual(result["parameter"], "video_id")
        self.assertTrue(result["retryable"])
        self.assertEqual(result["tool_name"], "youtube_get_transcript")

        document = etree.parse(str(ROOT / "data/partner_enrichment_tools.xml"))
        for code in document.xpath('//field[@name="code"]/text()'):
            namespace = {}
            exec(compile(code, "partner_enrichment_tool", "exec"), namespace)
            self.assertEqual(asyncio.run(namespace["execute"]()), "错误：必须提供 partner_id。")

    def test_chinese_titles_and_summary_are_not_forced_to_swedish(self):
        tree = ast.parse((ROOT / "models/ai_session.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "AICoworkerSession")
        methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
        namespace = {"re": re}
        for name in ("_title_prompt", "_final_summary_prompt", "_title_from_summary", "_clean_title"):
            node = methods[name]
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), "ai_session.py", "exec"), namespace)
        record = SimpleNamespace(env=SimpleNamespace(lang="zh_CN"), TITLE_MAX_CHARS=80,
                                 SUMMARY_HEADINGS=("Syfte", "Utfall", "Beslut", "Fakta", "Artefakter", "Open questions"))
        self.assertIn("简体中文", namespace["_title_prompt"](record, "查询员工"))
        self.assertIn("### 待解决问题", namespace["_final_summary_prompt"](record, "查询员工"))
        self.assertEqual(namespace["_title_from_summary"](record, "### 目的\n查询员工部门和岗位"), "查询员工部门和岗位")
        self.assertEqual(namespace["_clean_title"](record, "标题：员工资料查询"), "员工资料查询")
        self.assertEqual(namespace["_clean_title"](record, "### 目的"), "")


if __name__ == "__main__":
    unittest.main()
