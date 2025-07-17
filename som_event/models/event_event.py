# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class EventEvent(models.Model):
    _name = "event.event"
    _inherit = "event.event"

    _XML_ID_TAGS = {
        'channel': 'som_event.som_event_tag_category_channel',
        'scope': 'som_event.som_event_tag_category_scope',
        'sector': 'som_event.event_tag_category_sector',
        'type': 'som_event.event_tag_category_type',
    }

    def _get_tags_domain_by_type(self, tag_type):
        try:
            category_xml_id = self._XML_ID_TAGS.get(tag_type, None)
            if not category_xml_id:
                return [('id', '=', False)]
            category_id = self.env.ref(category_xml_id).id
            return [('category_id', '=', category_id)]
        except Exception as e:
            return [('id', '=', False)]

    @api.depends('date_begin', 'date_end')
    def _som_compute_duration(self):
        for record in self:
            record.som_duration_days = 0
            record.som_duration_hours = 0.0
            record.som_duration_display = "N/A"

            if record.date_begin and record.date_end:
                if record.date_end >= record.date_begin:
                    time_difference = record.date_end - record.date_begin

                    record.som_duration_days = time_difference.days
                    record.som_duration_hours = time_difference.total_seconds() / 3600.0

                    # Formated duration to display
                    if time_difference.days > 0:
                        record.som_duration_display = \
                            f"{time_difference.days} dies, {time_difference.seconds // 3600} hores"
                    else:
                        hours = time_difference.total_seconds() / 3600
                        minutes = (time_difference.total_seconds() % 3600) // 60
                        if hours >= 1:
                            record.som_duration_display = f"{int(hours)} hores, {int(minutes)} minuts"
                        elif minutes > 0:
                            record.som_duration_display = f"{int(minutes)} minuts"
                        else:
                            record.som_duration_display = "Menys d'un minut"

    som_channel_tag_id = fields.Many2one(
        comodel_name="event.tag",
        string="Canal",
        domain=lambda self: self._get_tags_domain_by_type("channel")
    )

    som_scope_tag_id = fields.Many2one(
        comodel_name="event.tag",
        string="Abast",
        domain=lambda self: self._get_tags_domain_by_type("scope")
    )

    som_sector_tag_id = fields.Many2one(
        comodel_name="event.tag",
        string="Sector",
        domain=lambda self: self._get_tags_domain_by_type("sector")
    )

    som_type_tag_id = fields.Many2one(
        comodel_name="event.tag",
        string="Tipus",
        domain=lambda self: self._get_tags_domain_by_type("type")
    )

    som_duration_days = fields.Integer(
        string='Duració (díes)',
        compute='_som_compute_duration',
        store=True  # Almacenar el valor para que sea buscable y filtrable
    )

    # Campo calculado para la duración en horas (opcional)
    som_duration_hours = fields.Float(
        string='Duració (hores)',
        compute='_som_compute_duration',
        store=True
    )

    som_duration_display = fields.Char(
        string='Duració',
        compute='_som_compute_duration',
        store=False,
        readonly=True,
    )

    # Option many2many
    # ----------------------
    # som_channel_tag_ids = fields.Many2many(
    #     "event.tag",
    #     string="Canal",
    #     relation="som_event_channel_rel",
    #     column1="event_id",
    #     column2="channel_tag_id",
    #     domain=lambda self: self._get_tags_domain_by_type("channel")
    # )
    #
    # som_scope_tag_ids = fields.Many2many(
    #     "event.tag",
    #     string="Abast",
    #     relation="som_event_scope_rel",
    #     column1="event_id",
    #     column2="scope_tag_id",
    #     domain=lambda self: self._get_tags_domain_by_type("scope")
    # )
    #
    # som_sector_tag_ids = fields.Many2many(
    #     "event.tag",
    #     string="Sector",
    #     relation="som_event_sector_rel",
    #     column1="event_id",
    #     column2="sector_tag_id",
    #     domain=lambda self: self._get_tags_domain_by_type("sector")
    # )
    #
    # som_type_tag_ids = fields.Many2many(
    #     "event.tag",
    #     string="Typus",
    #     relation="som_event_type_rel",
    #     column1="event_id",
    #     column2="type_tag_id",
    #     domain=lambda self: self._get_tags_domain_by_type("type")
    # )
