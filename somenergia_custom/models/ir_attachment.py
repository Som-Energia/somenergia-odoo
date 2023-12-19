# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, SUPERUSER_ID, tools, _
_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    pnt_type = fields.Selection(
        [('dni', 'DNI'), ('other', 'Otros')],
        string='Categoría',
        help="Especifica el tipus de document adjunt."
    )
