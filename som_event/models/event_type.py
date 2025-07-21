# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class EventType(models.Model):
    _name = "event.type"
    _inherit = "event.type"


    def _default_event_mail_type_ids(self):
        return False
