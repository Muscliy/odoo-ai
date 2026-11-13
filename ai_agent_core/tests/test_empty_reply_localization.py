"""Database-free regression checks for persisted empty reply translations."""

import ast
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import polib


ROOT = Path(__file__).resolve().parents[1]


class TestEmptyReplyLocalization(unittest.TestCase):
    def persist(self, answer, lang="zh_CN"):
        tree = ast.parse((ROOT / "controllers/stream.py").read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "_persist_stream_answer")
        namespace = {
            "_NO_ANSWER_MARKER": "(inget svar)",
            "_next_session_sequence": lambda env, session_id: 1,
            "fields": SimpleNamespace(Datetime=SimpleNamespace(now=lambda: None)),
            "_logger": logging.getLogger(__name__),
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]),
                     "stream.py", "exec"), namespace)
        catalog = {entry.msgid: entry.msgstr
                   for entry in polib.pofile(str(ROOT / "i18n/zh_CN.po"))}
        env = MagicMock()
        env._.side_effect = lambda text: catalog.get(text, text) if lang == "zh_CN" else text
        session = env["ai.coworker.session"].sudo().browse.return_value
        session.id = 1
        session.session_line_ids.sorted.return_value = []
        self.assertEqual(namespace["_persist_stream_answer"](env, 1, answer), 1)
        return env["ai.coworker.session.line"].sudo().create.call_args.args[0]["content"]

    def test_empty_reply_is_saved_in_chinese(self):
        self.assertEqual(self.persist(""), "（无回复）")

    def test_whitespace_reply_is_saved_in_chinese(self):
        self.assertEqual(self.persist(" \n "), "（无回复）")

    def test_actual_reply_is_preserved(self):
        self.assertEqual(self.persist("员工属于销售部"), "员工属于销售部")

    def test_other_languages_keep_source_fallback(self):
        self.assertEqual(self.persist("", "sv_SE"), "(inget svar)")


if __name__ == "__main__":
    unittest.main()
