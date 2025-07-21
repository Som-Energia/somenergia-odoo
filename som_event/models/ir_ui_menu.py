# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @api.returns("self")
    def get_user_roots(self):
        res = super().get_user_roots()
        if not self.env.user._is_admin() and \
                self.env.user.has_group("som_event.som_group_event_coll_user"):
            return self.env.ref("event.event_main_menu")
        return res
