"""Run the real alias compute method without a database or AI providers.

Only the method's decorator is removed. Fixtures expose the Odoo 19 company
fields, deliberately excluding the obsolete alias_domain_name attribute.
Run: python -m unittest discover -s ai_agent_core/tests -p test_coworker_alias_display.py
"""

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class MailTriggers(list):
    def filtered(self, predicate):
        return MailTriggers(item for item in self if predicate(item))

    def __getitem__(self, index):
        result = super().__getitem__(index)
        return MailTriggers(result) if isinstance(index, slice) else result

    @property
    def alias_id(self):
        return self[0].alias_id


class Coworkers(list):
    def __init__(self, records, company, catchall):
        super().__init__(records)
        parameters = Mock()
        parameters.sudo.return_value = parameters
        parameters.get_param.return_value = catchall
        self.env = Mock()
        self.env.company = company
        self.env.__getitem__ = Mock(return_value=parameters)


class TestCoworkerAliasDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "models/ai_coworker.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AICoworker")
        method = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == "_compute_alias_display")
        method.decorator_list = []
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
        cls.compute = staticmethod(namespace[method.name])

    def display(self, *, alias="assistant", domain=False, catchall=False, company_domain=False,
                email=False, use_env_company=False):
        company = SimpleNamespace(alias_domain_id=SimpleNamespace(name=company_domain), email=email)
        trigger = SimpleNamespace(init_type="mail", alias_id=SimpleNamespace(alias_domain=domain))
        record = SimpleNamespace(
            alias_name=alias, company_id=False if use_env_company else company,
            init_type_ids=MailTriggers([trigger] if domain else []),
        )
        self.compute(Coworkers([record], company, catchall))
        return record.alias_display

    def test_company_domain_without_legacy_field(self):
        self.assertEqual(self.display(company_domain="company.example"), "assistant@company.example")

    def test_alias_domain_has_priority(self):
        self.assertEqual(self.display(domain="alias.example", catchall="catchall.example",
                                      company_domain="company.example"), "assistant@alias.example")

    def test_catchall_has_priority_over_company(self):
        self.assertEqual(self.display(catchall="catchall.example", company_domain="company.example"),
                         "assistant@catchall.example")

    def test_company_email_fallback(self):
        self.assertEqual(self.display(email="info@company.example"), "assistant@company.example")

    def test_missing_domain_keeps_local_part(self):
        self.assertEqual(self.display(), "assistant")

    def test_missing_alias_is_false(self):
        self.assertFalse(self.display(alias=False, company_domain="company.example"))

    def test_environment_company_fallback(self):
        self.assertEqual(self.display(company_domain="env.example", use_env_company=True), "assistant@env.example")


if __name__ == "__main__":
    unittest.main()
