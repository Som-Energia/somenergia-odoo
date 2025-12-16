# -*- coding: utf-8 -*-
# To be executed in Odoo shell to reassign lead activities to the lead user

from tqdm import tqdm

# Search for leads not in stage 6 (won) and with assigned user
lead_ids = self.env['crm.lead'].search([('stage_id', '!=', 6),('user_id','!=', False)])

# Reassign activities to the lead user
for lead_id in tqdm(lead_ids):
	activity_ids = lead_id.activity_ids.filtered(lambda x: x.user_id != lead_id.user_id)
	activity_ids.write({'user_id': lead_id.user_id.id})

env.cr.commit()
