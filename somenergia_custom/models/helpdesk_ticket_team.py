from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    som_support_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Support partner",
    )
