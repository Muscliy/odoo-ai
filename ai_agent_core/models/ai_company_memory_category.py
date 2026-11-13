# -*- coding: utf-8 -*-
"""ai.company.memory.category — Kategorier med access-grupper för company memory."""

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AICompanyMemoryCategory(models.Model):
    _name = 'ai.company.memory.category'
    _description = 'Company Memory Category'
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True,
                       help='Kebab-case identifier, e.g. "customer-intelligence"')
    description = fields.Text(string='Description',
                               help='What this category contains')
    group_ids = fields.Many2many(
        'res.groups', string='Access Groups',
        help='User groups with access to this category. '
             'Empty = public (all company users can see).')
    active = fields.Boolean(string='Active', default=True)

    @api.depends('name')
    @api.depends_context('lang')
    def _compute_display_name(self):
        from .chinese_labels import MEMORY_CATEGORIES
        for record in self:
            record.display_name = (MEMORY_CATEGORIES.get(record.name, record.name)
                                   if (self.env.lang or '').startswith('zh') else record.name)

    @api.model
    def get_default_categories(self):
        """Seed data for default categories."""
        return [
            {'name': 'customer', 'description': '客户情报'},
            {'name': 'supplier', 'description': '供应商情报'},
            {'name': 'strategy', 'description': '战略管理'},
            {'name': 'marketing', 'description': '营销活动'},
            {'name': 'competitor', 'description': '竞争对手情报'},
            {'name': 'market', 'description': '市场情报'},
            {'name': 'management', 'description': '管理体系'},
            {'name': 'knowledge', 'description': '知识库'},
            {'name': 'website', 'description': '网站内容'},
            {'name': 'social', 'description': '社交媒体'},
            {'name': 'hr', 'description': '人事资料'},
            {'name': 'finance', 'description': '财务资料'},
            {'name': 'mgmt_summary', 'description': '管理摘要'},
            {'name': 'operations', 'description': '运营资料'},
        ]
