# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class Task(models.Model):
    _inherit = 'project.task'

    def name_get(self):
        res = []
        for task_id in self:
            name = "[#%s] %s" % (str(task_id.id), task_id.name)
            res += [(task_id.id, name)]
        return res
