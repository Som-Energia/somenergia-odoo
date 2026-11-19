# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    som_lead_integration_id = fields.Many2one(
        'som.crm.lead.integration', string='Collaborator integration',
        index=True, copy=False, ondelete='restrict',
    )
    id_external_lead = fields.Char(string='External lead ID', index=True, copy=False)
    som_intake_fingerprint = fields.Char(copy=False, groups='base.group_system')

    _sql_constraints = [
        ('som_external_lead_unique',
         'unique(som_lead_integration_id, id_external_lead)',
         'This external lead already exists for this integration.'),
        ('som_external_lead_required',
         "CHECK(som_lead_integration_id IS NULL OR "
         "(id_external_lead IS NOT NULL AND btrim(id_external_lead) <> ''))",
         'An external lead ID is required for collaborator opportunities.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        identity_fields = ('som_lead_integration_id', 'id_external_lead', 'som_intake_fingerprint')
        for vals in vals_list:
            has_identity = any(
                vals.get(key, self.env.context.get('default_' + key)) for key in identity_fields)
            if has_identity and not self.env.su:
                raise AccessError(_('External identities can only be created by the intake service.'))
        return super().create(vals_list)

    def write(self, vals):
        identity_fields = {'som_lead_integration_id', 'id_external_lead', 'som_intake_fingerprint'}
        if identity_fields.intersection(vals):
            for lead in self:
                current = {
                    'som_lead_integration_id': lead.som_lead_integration_id.id,
                    'id_external_lead': lead.id_external_lead,
                    'som_intake_fingerprint': lead.sudo().som_intake_fingerprint,
                }
                if any(vals[key] != current[key] for key in identity_fields.intersection(vals)):
                    raise ValidationError(_('The original external lead identity cannot be changed.'))
        return super().write(vals)

    @api.constrains('som_lead_integration_id', 'id_external_lead')
    def _check_intake_identity(self):
        for lead in self:
            if lead.id_external_lead and not lead.som_lead_integration_id:
                raise ValidationError(_('An external lead ID requires an integration.'))
