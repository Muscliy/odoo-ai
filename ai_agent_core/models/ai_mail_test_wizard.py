# -*- coding: utf-8 -*-
"""ai.coworker.mail.test.wizard — testa mail-flödet med en uppladdad .eml-fil."""

import base64
import email
import logging
import re
from email import policy

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AICoworkerMailTestWizard(models.TransientModel):
    _name = 'ai.coworker.mail.test.wizard'
    _description = 'Test the Mail Flow (eml)'

    coworker_id = fields.Many2one('ai.coworker', string='AI Medarbetare',
                                  required=True)
    eml_file = fields.Binary('E-postfil (.eml)', required=True)
    eml_filename = fields.Char('Filnamn')
    result = fields.Text('Resultat', readonly=True)
    state = fields.Selection([('input', 'Input'), ('done', 'Done')],
                             default='input')

    # ── .eml-parsning ────────────────────────────────────────────────────

    @staticmethod
    def _parse_eml(data):
        """Parsa en .eml-fil → (subject, email_from, body_text, attachments).

        attachments = [(filnamn, bytes, mimetype), ...]
        """
        msg = email.message_from_bytes(data, policy=policy.default)
        subject = msg.get('subject') or ''
        email_from = msg.get('From') or ''
        body_text = ''
        body_html = ''
        attachments = []
        for part in msg.walk():
            if part.is_multipart():
                continue
            fn = part.get_filename()
            if not fn:
                # Fallback: vissa klienter/program lägger filnamnet i
                # Content-Type-parametern (t.ex. "application/pdf; filename=..")
                fn = part.get_param('filename') or part.get_param('name')
            ctype = part.get_content_type()
            if fn:
                payload = part.get_payload(decode=True)
                if payload:
                    attachments.append((fn, payload, ctype))
            elif ctype == 'text/plain':
                try:
                    body_text = (part.get_content() or '').strip()
                except Exception:
                    body_text = ''
            elif ctype == 'text/html':
                try:
                    body_html = (part.get_content() or '').strip()
                except Exception:
                    body_html = ''
        if not body_text and body_html:
            body_text = re.sub(r'<[^>]+>', ' ', body_html)
            body_text = re.sub(r'\s+', ' ', body_text).strip()
        return subject, email_from, body_text, attachments

    @staticmethod
    def _attachment_text(fn, payload, mimetype, max_chars=6000):
        """Extrahera text ur en bilaga (PDF/text) för session-minnet."""
        head = f'Bilaga: {fn}\n'
        try:
            if mimetype == 'application/pdf':
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(payload))
                text = '\n'.join((p.extract_text() or '')
                                 for p in reader.pages)
                return head + (text.strip() or '(ingen text i PDF:en)')[:max_chars]
            if mimetype.startswith('text/'):
                return head + payload.decode(
                    'utf-8', errors='replace')[:max_chars]
            return head + '(binary attachment — see ir.attachment)'
        except Exception as e:
            return head + f'(kunde inte extrahera text: {e})'

    # ── Kör ──────────────────────────────────────────────────────────────

    def action_run(self):
        """Ladda upp .eml → skapa session → bilagor/minnen → dispatch."""
        self.ensure_one()
        if not self.eml_file:
            raise UserError(self.env._('Upload an .eml file first.'))
        if not self.coworker_id:
            raise UserError(self.env._('Choose an AI Coworker.'))

        data = base64.b64decode(self.eml_file)
        subject, email_from, body, attachments = self._parse_eml(data)
        coworker = self.coworker_id

        # Skapa sessionen (samma som mailgateway/message_new)
        session = self.env['ai.coworker.session'].with_context(
            mail_create_nosubscribe=True).create({'coworker_id': coworker.id})
        session.name = (subject or 'Inkommande mail')[:80]

        # Bilagor → ir.attachment + session-minnen (tillgängliga för agenter
        # via _build_injection_prompt, som injicerar session.memory_ids).
        att_count = 0
        for fn, payload, mimetype in attachments:
            self.env['ir.attachment'].create({
                'name': fn,
                'res_model': 'ai.coworker.session',
                'res_id': session.id,
                'datas': base64.b64encode(payload),
                'mimetype': mimetype,
                'type': 'binary',
            })
            self.env['ai.memory'].create({
                'name': fn,
                'content': self._attachment_text(fn, payload, mimetype),
                'memory_type': 'text',
                'session_id': session.id,
                'quest_id': coworker.id,
                'category': 'fact',
            })
            att_count += 1

        msg = {
            'subject': subject,
            'email_from': email_from,
            'body': body,
            'attachment_ids': [],
        }
        session._dispatch_mail(coworker, msg)

        self.write({
            'state': 'done',
            'result': (
                self.env._(
                    'Session %(id)s created: %(name)s\nSender: %(sender)s\n'
                    'Attachments: %(count)s → attachments and session memories\n\n'
                    'Open the session (Odoo Mind → Sessions) to see the email, attachments and reply.',
                    id=session.id, name=session.name, sender=email_from or self.env._('Unknown'), count=att_count,
                )
            ),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Mail-test klart'),
                'message': self.env._('Session {0} skapad — {1} bilagor.').format(session.id, att_count),
                'sticky': False,
                'type': 'info',
            },
        }

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
