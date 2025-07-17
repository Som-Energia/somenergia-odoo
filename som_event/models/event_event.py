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
