# -*- coding: utf-8 -*-
"""hr.employee extension — AI-medarbetare i samma vy som människor."""

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_ai = fields.Boolean(
        'AI-medarbetare',
        default=False,
        help='True if this is an AI Coworker (ai.coworker). Used to filter and distinguish in views.')

    ai_coworker_id = fields.Many2one(
        'ai.coworker', string='AI Coworker',
        help='The matching ai.coworker if this employee is an AI.')

    # Överskugga name för att visa 🤖-prefix i vyer
    @api.depends("name", "is_ai")
    def _compute_display_name(self):
        super()._compute_display_name()
        for employee in self:
            if employee.is_ai:
                employee.display_name = f"🤖 {employee.display_name}"
