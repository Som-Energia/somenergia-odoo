# -*- coding: utf-8 -*-
# To be excecuted in Odoo shell to recompute timesheets costs where amount=0 but unit_amount>0
from odoo.tests.common import Form
from tqdm import tqdm

aal_ids = self.env['account.analytic.line'].search([
    ('user_id', 'in', [222, 182]), # IDs of users to recompute
    ('project_id', '!=', False),
    ('unit_amount', '>', 0),
    ('amount', '=', 0),
])

for aal_id in tqdm(aal_ids):
     with Form(aal_id) as f:
       f.unit_amount = aal_id.unit_amount

env.cr.commit()
