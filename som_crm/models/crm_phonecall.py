# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _, _lt
from odoo.exceptions import ValidationError


try:
    import phonenumbers
except ImportError:
    pass

_logger = logging.getLogger(__name__)


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall']

    som_phone_call_result_id = fields.Many2one(
        'phone.call.result',
        string='Phone Call Result',
        help="Result of the phone call"
    )

    def _get_user_crm(self):
        user_id = self.env['res.users'].search([
            ('som_call_center_user', '=', self.som_operator),
        ], limit = 1)
        return user_id or False

    def _prepare_opportunity_vals(self):
        res = super()._prepare_opportunity_vals()

        utm_medium_phone_id = self.env.ref('utm.utm_medium_phone', raise_if_not_found=False) or False
        user_id = self._get_user_crm()

        name = f'Lead from phonecall {self.som_phone}'
        res.update({'name': name})

        res.update({
            'medium_id': utm_medium_phone_id.id if utm_medium_phone_id else False,
            'contact_name': self.som_caller_name,
            'email_from': self.email_from,
            'phone': self.som_phone,
            'vat': self.som_caller_vat,
            'user_id': user_id.id if user_id else False,
            'lang_id': False,
        })
        return res

    @api.model
    def _convert_to_opportunity_by_category(self):
        crm_category_id = self.env.company.som_crm_call_category_id
        pc_ids = self.env['crm.phonecall'].search([
            ('som_category_ids', 'in', [crm_category_id.id]),
            ('opportunity_id', '=', False),
            ('som_phone', '!=', False),
            ('direction', '=', 'in'),
        ])
        _logger.info(f"Phone calls to convert: {len(pc_ids)}")
        # We do it with a for because the function is ensure_one
        for pc_id in pc_ids:
            pc_id._assign_to_opportunity()
            # pc_id.action_button_convert2opportunity()
        _logger.info(f"{len(pc_ids)} Phone calls converted successfully")

    @api.model
    def _assign_partner_with_opportunity(self):
        pc_ids = self.env['crm.phonecall'].search([
            ('opportunity_id', '!=', False),
            ('partner_id', '=', False),
            ('opportunity_id.partner_id', '!=', False),
        ])

        _logger.info(f"Phone calls to assign partner: {len(pc_ids)}")
        for pc_id in pc_ids:
            pc_id.partner_id = pc_id.opportunity_id.partner_id
        _logger.info(f"{len(pc_ids)} Phone calls assigned partner successfully")

    @api.model
    def _get_parsed_phone_number(self, number):
        try:
            p = phonenumbers.parse(number, "ES")
            digits = str(p.national_number)
            if len(digits) == 9:
                a, b, c, d = digits[:3], digits[3:5], digits[5:7], digits[7:9]
                return f'+34 {a} {b} {c} {d}'
            else:
                return number
        except Exception as e:
            return number

    def action_button_convert2opportunity(self):
        self.ensure_one()
        if self.env.user.som_call_center_user != self.som_operator:
            return {
                'name': 'Convert Call to Opportunity',
                'type': 'ir.actions.act_window',
                'res_model': 'convert.call.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_phonecall_id': self.id}
            }
        res = self.do_action_button_convert2opportunity()
        return res

    def do_action_button_convert2opportunity(self):
        self.ensure_one()
        if not self.som_phone:
            raise ValidationError(
                _("The call must have a phone number to be converted to an opportunity.")
            )
        oppo_id = self._assign_to_opportunity()
        if oppo_id:
            return oppo_id.redirect_lead_opportunity_view()
        else:
            raise ValidationError(_("No opportunity found to open."))

    def _assign_to_opportunity(self):
        self.ensure_one()
        if self.opportunity_id:
            self.opportunity_id
        oppo_id = self._find_matching_opportunity()
        if not oppo_id:
            oppo_id = self.env["crm.lead"].create(self._prepare_opportunity_vals())
        self.write({"opportunity_id": oppo_id.id, "state": "done"})
        # add tag to opportunity
        self.sudo().env.company.som_ff_call_to_opportunity = False
        crm_category_id = self.env.company.som_crm_call_category_id
        if crm_category_id and crm_category_id not in self.som_category_ids:
            self.write({'som_category_ids': [(4, crm_category_id.id)]})

        return oppo_id

    def _find_matching_opportunity(self):
        self.ensure_one()
        if not self.som_phone:
            return False
        phone_sanitized = ""
        parsed_number = ""
        try:
            parsed_number = phonenumbers.parse(self.som_phone, "ES")
            phone_sanitized = f"+{parsed_number.country_code}{parsed_number.national_number}"
        except Exception as e:
            pass
        domain = [
            ('type', '=', 'opportunity'),
            '|',
            ('phone', '=', parsed_number),
            ('phone_sanitized', '=', phone_sanitized),
        ]
        opportunity_id = self.env['crm.lead'].search(domain, limit=1)
        return opportunity_id if len(opportunity_id) == 1 else False

    # TODO: Tests
    @api.model
    def auto_create_opportunity(self, vals):
        if self.env.company.som_ff_call_to_opportunity and self.env.company.som_crm_call_category_id and vals.get('som_category_ids', False):
            list_categories = vals.get('som_category_ids', [])[0][2]
            if self.env.company.som_crm_call_category_id.id in list_categories :
                return True
        return False

    @api.model
    def create(self, vals):
        phonecall_id = super(CrmPhonecall, self).create(vals)
        if self.auto_create_opportunity(vals):
            phonecall_id._assign_to_opportunity()
        return phonecall_id

    def write(self, vals):
        result = super(CrmPhonecall, self).write(vals)
        if self.auto_create_opportunity(vals):
            for phonecall_id in self.filtered(lambda x: not x.opportunity_id):
                phonecall_id._assign_to_opportunity()
        return result

    def button_open_phonecall(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm_phonecall.crm_case_categ_phone_incoming0"
        )
        action['context'] = {
            "default_opportunity_id": self.id,
            "search_default_opportunity_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_duration": 1.0,
        }
        return action


class ConvertCallWizard(models.TransientModel):
    _name = 'convert.call.wizard'
    _description = 'Convert Call to Opportunity Wizard'

    phonecall_id = fields.Many2one('crm.phonecall', string="Call", required=True)
    message = fields.Char(
        string = "Confirm Message",
        default = _("This call is not yours. Are you sure you want to convert it to opportunity? In that case, remember to assign it to yourself."),
        required = True
    )

    def action_confirm(self):
        self.ensure_one()
        return self.phonecall_id.do_action_button_convert2opportunity()
