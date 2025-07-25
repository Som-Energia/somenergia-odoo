import logging
from odoo.api import Environment, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    migration script: replace implied 'group_hr_timesheet_user' with 'som_group_hr_timesheet_department_id'.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    _logger.info("Executing migration script'")

    try:
        group_hr_timesheet_user_id = env.ref('hr_timesheet.group_hr_timesheet_user', raise_if_not_found=False)
        som_group_hr_timesheet_department_id = env.ref(
            'somenergia_custom.som_group_hr_timesheet_department', raise_if_not_found=True
        )
        group_hr_timesheet_approver_id = env.ref('hr_timesheet.group_hr_timesheet_approver', raise_if_not_found=False)

        if group_hr_timesheet_approver_id and som_group_hr_timesheet_department_id:
            ids_final_implied = group_hr_timesheet_approver_id.implied_ids.filtered(
                lambda x: not group_hr_timesheet_user_id or x.id != group_hr_timesheet_user_id.id
            ).ids

            ids_final_implied.append(som_group_hr_timesheet_department_id.id)

            group_hr_timesheet_approver_id.write({'implied_ids': [(6, 0, ids_final_implied)]})

        _logger.info("Migration script executed successfully'")

    except Exception as e:
        _logger.error('Error executing migration script: %s', e)
