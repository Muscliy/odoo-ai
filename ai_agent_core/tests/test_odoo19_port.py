"""Odoo 19 installation, inherited access, constraints and provider regressions."""
import asyncio
from unittest.mock import AsyncMock, patch

from psycopg2.errors import UniqueViolation

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged

from ..core.provider import AIProvider, Message, Role
from ..hooks import pre_init_hook_check_conflicts


@tagged("post_install", "-at_install", "odoo19_port")
class TestOdoo19Port(TransactionCase):
    def test_inherited_group_sql_access(self):
        child = self.env["res.groups"].create({"name": "Port read permission"})
        parent = self.env["res.groups"].create({
            "name": "Port inherited permission", "implied_ids": [Command.link(child.id)],
        })
        user = self.env["res.users"].create({
            "name": "Port reader", "login": "vertel-port-reader",
            "group_ids": [Command.set([self.env.ref("base.group_user").id, parent.id])],
        })
        self.env["ir.model.access"].create({
            "name": "Port log reader", "model_id": self.env.ref("base.model_ir_logging").id,
            "group_id": child.id, "perm_read": True,
        })
        self.env.flush_all()
        self.env.cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid = %s", [user.id])
        self.assertNotIn(child.id, [row[0] for row in self.env.cr.fetchall()])
        self.assertIn(child, user.all_group_ids)
        self.env.cr.execute("SELECT ai_okf_can_read(%s, 'ir.logging')", [user.id])
        self.assertTrue(self.env.cr.fetchone()[0])
        parent.implied_ids = [Command.clear()]
        self.env.flush_all()
        self.env.cr.execute("SELECT ai_okf_can_read(%s, 'ir.logging')", [user.id])
        self.assertFalse(self.env.cr.fetchone()[0])

    def test_message_sequence_constraint_is_enforced(self):
        session = self.env["ai.coworker.session"].create({
            "coworker_id": self.env.ref("ai_agent_core.coworker_default_assistent").id,
        })
        lines = self.env["ai.coworker.session.line"]
        values = {"session_id": session.id, "sequence": 1, "role": "user", "content": "Hello"}
        lines.create(values)
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            lines.create(values)
            self.env.flush_all()

    def test_oca_installation_is_rejected(self):
        self.env["ir.module.module"].create({"name": "ai_tool", "state": "installed"})
        self.env.flush_all()
        with self.assertRaisesRegex(UserError, "OCA ai_tool"):
            pre_init_hook_check_conflicts(self.env)

    def test_preinstall_prerequisites(self):
        pre_init_hook_check_conflicts(self.env)

    def test_push_is_optional(self):
        self.assertNotIn("web.pwa.push", self.env)
        self.env["ai.coworker.session"]._push_done_notification()

    def test_hr_ai_display_name(self):
        employee = self.env["hr.employee"].create({"name": "Port AI", "is_ai": True})
        self.assertTrue(employee.display_name.startswith("🤖 "))
        employee.is_ai = False
        self.assertFalse(employee.display_name.startswith("🤖 "))

    def test_provider_parses_tool_call_without_external_request(self):
        provider = AIProvider(base_url="https://example.invalid/v1", api_key="test-placeholder")
        payload = {"choices": [{"message": {"content": "", "tool_calls": [{
            "id": "call_1", "type": "function", "function": {
                "name": "search", "arguments": '{"model":"res.partner"}',
            },
        }]}, "finish_reason": "tool_calls"}]}
        with patch.object(provider, "_post", new=AsyncMock(return_value=payload)):
            reply = asyncio.run(provider.chat("test-model", [Message(role=Role.USER, content="Search")]))
        self.assertEqual(reply.tool_calls[0].name, "search")
        self.assertEqual(reply.tool_calls[0].arguments, {"model": "res.partner"})

    def test_backend_assets_compile(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_backend")
        self.assertTrue(bundle.js())
        self.assertTrue(bundle.css())
        self.assertFalse(bundle.css_errors)


@tagged("post_install", "-at_install", "odoo19_port")
class TestOdoo19Http(HttpCase):
    def test_backend_in_browser(self):
        action = self.env.ref("ai_agent_core.action_ai_orchestration_dashboard")
        self.browser_js(
            f"/odoo/action-{action.id}",
            "console.log('test successful');",
            ready="document.querySelector('.o_kanban_view') !== null",
            login="admin", timeout=40,
        )

    def test_chat_and_backend_pages(self):
        self.authenticate("admin", "admin")
        response = self.url_open("/ai/chat")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertNotIn("Traceback", response.text)
        response = self.url_open("/odoo")
        self.assertEqual(response.status_code, 200)
