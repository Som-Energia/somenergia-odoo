# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase, tagged


@tagged("som_openproject")
class TestOpenProjectImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AnalyticLine = cls.env["account.analytic.line"]
        cls.env.company.som_timesheet_lock_date = False
        cls.user = new_test_user(
            cls.env,
            login="openproject_import_test_user",
            groups="base.group_user",
        )
        cls.employee = cls.env["hr.employee"].create({
            "name": "OpenProject Import Employee",
            "user_id": cls.user.id,
        })
        cls.project = cls.env["project.project"].create({
            "name": "OpenProject CeCo Project",
        })
        cls.work_package_project = cls.env["project.project"].create({
            "name": "OpenProject Work Package CeCo",
        })
        date_from = datetime(2026, 7, 20, 0, 0, 0)
        cls.week = cls.env["som.calendar.week"].create({
            "name": "2026-W30",
            "som_cw_code": "2026W30",
            "som_cw_date": date_from,
            "som_cw_date_end": date_from + timedelta(days=6),
            "som_cw_week_number": 30,
            "som_cw_week_year": 2026,
            "som_cw_year": 2026,
        })
        cls.worked_week = cls.env["som.worked.week"].create({
            "som_week_id": cls.week.id,
            "som_employee_id": cls.employee.id,
        })

    def _source_entry(self, entry_id, **overrides):
        source = {
            "openproject_time_entry_id": entry_id,
            "date": "2026-07-20",
            "openproject_hours": "PT1H30M",
            "unit_amount": 1.5,
            "comment": "OpenProject test entry",
            "openproject_work_package_subject": "OpenProject work package",
            "openproject_user_login": self.user.login,
            "openproject_project_ceco": self.project.name,
            "openproject_work_package_ceco": False,
        }
        source.update(overrides)
        return source

    def test_import_creates_immutable_timesheet_with_source_data(self):
        source = self._source_entry(1001)

        stats = self.AnalyticLine._import_openproject_source_entries([source])

        line = self.AnalyticLine.search([("oproject_entry_id", "=", 1001)])
        self.assertEqual(stats, {"created": 1, "duplicates": 0, "skipped": 0})
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.project_id, self.project)
        self.assertEqual(line.som_week_id, self.week)
        self.assertEqual(line.som_worked_week_id, self.worked_week)
        self.assertEqual(line.unit_amount, 1.5)
        self.assertEqual(line.name, source["openproject_work_package_subject"])
        self.assertEqual(line.oproject_source_data, source)

    def test_import_prefers_work_package_ceco(self):
        stats = self.AnalyticLine._import_openproject_source_entries([
            self._source_entry(
                1002,
                openproject_work_package_ceco=self.work_package_project.name,
            )
        ])

        line = self.AnalyticLine.search([("oproject_entry_id", "=", 1002)])
        self.assertEqual(stats["created"], 1)
        self.assertEqual(line.project_id, self.work_package_project)

    def test_import_skips_existing_openproject_entry(self):
        source = self._source_entry(1003)
        self.AnalyticLine._import_openproject_source_entries([source])

        stats = self.AnalyticLine._import_openproject_source_entries([source])

        self.assertEqual(stats, {"created": 0, "duplicates": 1, "skipped": 0})
        self.assertEqual(
            self.AnalyticLine.search_count([("oproject_entry_id", "=", 1003)]),
            1,
        )

    def test_imported_external_id_cannot_be_changed(self):
        self.AnalyticLine._import_openproject_source_entries([
            self._source_entry(1005)
        ])
        line = self.AnalyticLine.search([("oproject_entry_id", "=", 1005)])

        with self.assertRaises(UserError):
            line.write({"oproject_entry_id": 1006})

    def test_import_skips_entry_without_ceco(self):
        stats = self.AnalyticLine._import_openproject_source_entries([
            self._source_entry(
                1004,
                openproject_project_ceco=False,
                openproject_work_package_ceco=False,
            )
        ])

        self.assertEqual(stats, {"created": 0, "duplicates": 0, "skipped": 1})
        self.assertFalse(
            self.AnalyticLine.search([("oproject_entry_id", "=", 1004)])
        )

    def test_week_range_starts_on_execution_week_monday(self):
        date_from, date_to = self.AnalyticLine._get_openproject_week_range(
            "2026-07-23"
        )

        self.assertEqual(str(date_from), "2026-07-20")
        self.assertEqual(str(date_to), "2026-07-26")
