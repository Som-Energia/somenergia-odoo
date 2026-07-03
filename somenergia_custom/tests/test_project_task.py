# -*- coding: utf-8 -*-
from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('som_project_task')
class TestProjectTask(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.area_tag = cls.env.ref('somenergia_custom.som_project_tag_area')

    @freeze_time('2026-02-16')
    def test_task_service_project_domain_uses_current_date_validity(self):
        today = fields.Date.today()
        old_project = self.env['project.project'].create({
            'name': 'Expired Area Project',
            'tag_ids': [(6, 0, [self.area_tag.id])],
            'date': today - timedelta(days=1),
        })
        current_project = self.env['project.project'].create({
            'name': 'Current Area Project',
            'tag_ids': [(6, 0, [self.area_tag.id])],
            'date_start': today,
        })
        future_project = self.env['project.project'].create({
            'name': 'Future Area Project',
            'tag_ids': [(6, 0, [self.area_tag.id])],
            'date_start': today + timedelta(days=7),
        })
        timeless_project = self.env['project.project'].create({
            'name': 'Timeless Area Project',
            'tag_ids': [(6, 0, [self.area_tag.id])],
        })
        non_area_project = self.env['project.project'].create({
            'name': 'Non Area Project',
        })

        task = self.env['project.task'].create({
            'name': 'Task Domain Test',
            'project_id': timeless_project.id,
        })
        task._compute_project_type_domain_ids()

        self.assertNotIn(old_project, task.som_project_area_domain_ids)
        self.assertIn(current_project, task.som_project_area_domain_ids)
        self.assertNotIn(future_project, task.som_project_area_domain_ids)
        self.assertIn(timeless_project, task.som_project_area_domain_ids)
        self.assertNotIn(non_area_project, task.som_project_area_domain_ids)
