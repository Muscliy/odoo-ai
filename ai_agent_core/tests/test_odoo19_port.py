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
    def test_ai_backend_visuals_in_browser(self):
        """Informational badges stay neutral; real status badges stay semantic."""
        from odoo.tests.common import ChromeBrowser

        self.env.ref("base.user_admin").lang = "zh_CN"
        model = self.env["ai.model"].create({
            "name": "ui-preview", "provider": self.env.ref("ai_agent_core.provider_deepseek").id,
            "is_vision": True, "has_streaming": True, "cost_input_1k": 0.01,
        })
        self.env.ref("ai_agent_core.agent_default_core").model_id = model
        original_wait = ChromeBrowser._wait_code_ok
        code = """
            const root = document.querySelector('.o_ai_kanban');
            if (root.querySelector('.fa-android')) throw new Error('Legacy Android placeholder');
            for (const badge of root.querySelectorAll('.o_ai_metadata_badge')) {
                if (getComputedStyle(badge).outlineStyle !== 'none') {
                    throw new Error('Metadata must not have a decorative accent outline');
                }
                const color = getComputedStyle(badge).backgroundColor.match(/[\\d.]+/g).map(Number);
                if (Math.max(...color.slice(0, 3)) - Math.min(...color.slice(0, 3)) > 20) {
                    throw new Error('Informational badges must use a neutral background');
                }
            }
            for (const badge of root.querySelectorAll('.badge.text-bg-success')) {
                const color = getComputedStyle(badge).backgroundColor.match(/[\\d.]+/g).map(Number);
                if (color.length < 4 || color[3] > 0.15) {
                    throw new Error('Status badge must use a subtle semantic background');
                }
            }
            if (document.documentElement.scrollWidth > window.innerWidth + 2) {
                throw new Error('Page must not overflow horizontally');
            }
            console.log('test successful');
        """
        actions = ["action_ai_agent", "action_ai_coworker", "action_ai_provider", "action_ai_model", "action_ai_skill"]
        for name, width in [(name, 1440) for name in actions] + [("action_ai_agent", 390)]:
            def check_layout(browser, script, timeout, error_checker=None):
                browser._websocket_request("Emulation.setDeviceMetricsOverride", params={
                    "width": width, "height": 1000, "deviceScaleFactor": 1, "mobile": False,
                })
                return original_wait(browser, script, timeout, error_checker=error_checker)

            action = self.env.ref("ai_agent_core." + name)
            with self.subTest(action=name, width=width), patch.object(ChromeBrowser, "_wait_code_ok", check_layout):
                self.browser_js(
                    f"/odoo/action-{action.id}", code,
                    ready="document.querySelector('.o_ai_kanban .o_kanban_record') !== null",
                    login="admin", timeout=40,
                )

    def test_settings_layout_in_browser(self):
        """Default chat setup stays visible and numeric rows fit narrow screens."""
        from odoo.tests.common import ChromeBrowser

        self.env.ref("base.user_admin").lang = "zh_CN"
        action = self.env.ref("ai_agent_core.action_ai_settings")
        original_wait = ChromeBrowser._wait_code_ok
        code = """
            const app = document.querySelector('.app_settings_block[data-key="ai_agent_core"]');
            const firstSetting = app.querySelector('.o_setting_box');
            if (firstSetting.id !== 'agent_default_coworker') {
                throw new Error('Default coworker must be the first setting');
            }
            if (!firstSetting.innerText.includes('默认 AI 员工')) {
                throw new Error('Default coworker label must be translated');
            }
            if (app.innerText.includes('Warning threshold') || app.innerText.includes('tecken')) {
                throw new Error('Memory budget labels must be translated');
            }
            if (firstSetting.querySelector('details').open) {
                throw new Error('Long guidance should start collapsed');
            }
            if (app.scrollWidth > app.clientWidth + 2) {
                throw new Error('Settings must not overflow horizontally');
            }
            for (const field of app.querySelectorAll('.o_field_integer.oe_inline')) {
                if (field.getBoundingClientRect().width > 120) {
                    throw new Error('Inline numeric fields must stay compact');
                }
            }
            console.log('test successful');
        """

        for width in (1440, 390):
            def check_layout(browser, script, timeout, error_checker=None):
                browser._websocket_request("Emulation.setDeviceMetricsOverride", params={
                    "width": width, "height": 1000, "deviceScaleFactor": 1,
                    "mobile": False,
                })
                return original_wait(browser, script, timeout, error_checker=error_checker)

            with self.subTest(width=width), patch.object(ChromeBrowser, "_wait_code_ok", check_layout):
                self.browser_js(
                    f"/odoo/action-{action.id}", code,
                    ready="document.querySelector('#agent_default_coworker') !== null",
                    login="admin", timeout=40,
                )

    def test_backend_in_browser(self):
        action = self.env.ref("ai_agent_core.action_ai_orchestration_dashboard")
        self.browser_js(
            f"/odoo/action-{action.id}",
            "console.log('test successful');",
            ready="document.querySelector('.o_kanban_view') !== null",
            login="admin", timeout=40,
        )

    def test_chat_theme_in_browser(self):
        """Chat uses backend theme assets and remains usable on narrow screens."""
        from odoo.tests.common import ChromeBrowser

        self.env.ref("base.user_admin").lang = "zh_CN"
        original_wait = ChromeBrowser._wait_code_ok
        code = """
            const root = document.documentElement;
            const prompt = document.querySelector('#prompt-input');
            if (root.dataset.theme !== 'light') throw new Error('Default theme must be light');
            if (!document.querySelector('link[href*="assets_chat"]')) {
                throw new Error('Chat must load the backend theme stylesheet');
            }
            if (!document.querySelector('.welcome-title').innerText.includes('开始新的对话')) {
                throw new Error('Welcome copy must use the Chinese catalog');
            }
            if (!document.querySelector('.chat-composer-hint').innerText.includes('按 Enter 发送')) {
                throw new Error('Composer hint must use the Chinese catalog');
            }
            if (getComputedStyle(document.querySelector('.chat-heading h1')).fontWeight !== '700') {
                throw new Error('Chat heading must use the system type scale');
            }
            if (root.scrollWidth > window.innerWidth + 2) throw new Error('Horizontal overflow');
            const inputBounds = prompt.getBoundingClientRect();
            if (inputBounds.width < 100 || inputBounds.bottom > window.innerHeight) {
                throw new Error('Composer must fit the viewport');
            }
            document.querySelector('#theme-btn').click();
            if (root.dataset.theme !== 'dark') throw new Error('Dark theme toggle failed');
            document.querySelector('#theme-btn').click();
            if (window.innerWidth <= 768) {
                document.querySelector('.hamburger').click();
                if (!document.querySelector('#sidebar').classList.contains('open')) {
                    throw new Error('Mobile history navigation did not open');
                }
                document.querySelector('#sidebar-overlay').click();
            }
            prompt.value = '只检查输入框，不发送';
            prompt.dispatchEvent(new Event('input', {bubbles: true}));
            prompt.value = '';
            console.log('test successful');
        """

        for width in (1440, 390):
            def check_layout(browser, script, timeout, error_checker=None):
                browser._websocket_request("Emulation.setDeviceMetricsOverride", params={
                    "width": width, "height": 1000, "deviceScaleFactor": 1,
                    "mobile": False,
                })
                return original_wait(browser, script, timeout, error_checker=error_checker)

            with self.subTest(width=width), patch.object(ChromeBrowser, "_wait_code_ok", check_layout):
                self.browser_js(
                    "/ai/chat", code,
                    ready=("document.readyState === 'complete' && typeof window.toggleTheme === 'function'"
                           " && document.querySelector('#prompt-input') !== null"),
                    login="admin", timeout=40,
                )

    def test_chat_and_backend_pages(self):
        self.authenticate("admin", "admin")
        response = self.url_open("/ai/chat")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertNotIn("Traceback", response.text)
        self.assertIn('rel="shortcut icon" href="/web/binary/company_logo"', response.text)
        self.assertNotIn('class="open-odoo-btn"', response.text)
        response = self.url_open("/odoo")
        self.assertEqual(response.status_code, 200)
