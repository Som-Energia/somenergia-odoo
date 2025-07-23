# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # remove event groups assigned by default when install event module
    event_group_admin_id = env.ref('event.group_event_manager')
    event_group_user_id = env.ref('event.group_event_user')
    event_group_registration_id = env.ref('event.group_event_registration_desk')

    user_ids = env['res.users'].search([
        ('id', '!=', env.ref('base.user_root').id),
        ('active', '=', True),
    ])

    for user_id in user_ids:
        m2m_commands = []
        if event_group_admin_id.id in user_id.groups_id.ids:
            m2m_commands.append((3, event_group_admin_id.id))

        if event_group_user_id.id in user_id.groups_id.ids:
            m2m_commands.append((3, event_group_user_id.id))

        if event_group_registration_id.id in user_id.groups_id.ids:
            m2m_commands.append((3, event_group_registration_id.id))

        if m2m_commands:
            user_id.write({'groups_id': m2m_commands})
