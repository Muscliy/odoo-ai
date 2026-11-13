"""Regressions for the Odoo 19 LLM model and token-tracking references."""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "odoo19_port")
class TestLLMOdoo19(TransactionCase):
    def test_token_tracking_uses_coworker_models(self):
        coworker = self.env.ref("ai_agent_core.coworker_default_assistent")
        session = self.env["ai.coworker.session"].create({"coworker_id": coworker.id})
        line = self.env["llm.session.line"].create({
            "session_id": session.id, "quest_id": coworker.id,
            "input_tokens": 12, "output_tokens": 8,
        })
        self.assertEqual(line.session_id, session)
        self.assertEqual(line.quest_id, coworker)
        self.assertEqual(line.total_tokens, 20)

    def test_model_display_name_tracks_state(self):
        model = self.env["llm.model"].create({"name": "test-model", "provider_type": "custom"})
        self.assertEqual(model.display_name, "test-model (custom)")
        model.active = False
        self.assertEqual(model.display_name, "test-model (custom) [inactive]")
