from odoo import api, fields, models, tools, _


class IiUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @api.returns("self")
    def get_user_roots(self):
        res = super().get_user_roots()
        if not self.env.user._is_admin() and \
                self.env.user.has_group("somenergia_custom.som_group_project_coll_user"):
            return self.env.ref("project.menu_main_pm")
        return res
