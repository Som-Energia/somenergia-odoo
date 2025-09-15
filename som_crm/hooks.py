# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # update name of existing stages
    _logger.info("Getting stages to be updated")

    stage_lead1_id = env.ref('crm.stage_lead1', raise_if_not_found=False)
    stage_lead2_id = env.ref('crm.stage_lead2', raise_if_not_found=False)
    stage_lead3_id = env.ref('crm.stage_lead3', raise_if_not_found=False)
    stage_lead4_id = env.ref('crm.stage_lead4', raise_if_not_found=False)

    if stage_lead1_id:
        stage_lead1_id.write({'name': 'Pending 1st contact'})
        stage_lead1_id.with_context(lang='ca_ES').write({'name': 'Pendent 1r contacte'})
        stage_lead1_id.with_context(lang='es_ES').write({'name': 'Pendiente 1er contacto'})

    if stage_lead2_id:
        stage_lead2_id.write({'name': 'Pending 1st contact and simulation'})
        stage_lead2_id.with_context(lang='ca_ES').write({'name': 'Pendent 1r contacte i simulació'})
        stage_lead2_id.with_context(lang='es_ES').write({'name': 'Pendiente 1er contacto y simulación'})

    if stage_lead3_id:
        stage_lead3_id.write({'name': 'Pending simulation or comparison'})
        stage_lead3_id.with_context(lang='ca_ES').write({'name': 'Penent simulació o comparativa'})
        stage_lead3_id.with_context(lang='es_ES').write({'name': 'Pendiente simulación o comparativa'})

    if stage_lead4_id:
        stage_lead4_id.write({
            'name': 'Simulation or comparison sent',
            'is_won': False,
            'sequence': 4,
        })
        stage_lead4_id.with_context(lang='ca_ES').write({'name': 'Simulació o comparativa enviada'})
        stage_lead4_id.with_context(lang='es_ES').write({'name': 'Simulación o comparativa enviada'})

    _logger.info("Modified som_crm stage records with translations")
