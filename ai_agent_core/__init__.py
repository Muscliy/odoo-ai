# -*- coding: utf-8 -*-
"""AI Agent Core for Odoo 19; required imports must fail visibly."""
from . import hooks, models, controllers, wizards
from .hooks import post_init_hook, post_init_hook_personal_memory, pre_init_hook_check_conflicts
from . import http_guard
from .core.channels import register_chat_channel, register_mail_channel

http_guard.install()
register_mail_channel()
register_chat_channel()
