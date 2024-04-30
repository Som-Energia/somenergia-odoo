# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _, _lt
from odoo.modules.module import get_module_resource
from odoo.addons.odoo_callinfo.pydantic.pydantic_models import Employee
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import Categories
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import Category
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import NewCall
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import Call
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import CallLog
from odoo.addons.odoo_callinfo.pydantic.callinfo_models import UpdatedCallLog
from odoo.exceptions import UserError, ValidationError
from pydantic import ValidationError
from datetime import datetime

import json


class SomCallInfoEndpoint(models.AbstractModel):
    _name = 'som.callinfo.endpoint'
    _description = 'Som CallInfo Endpoint'

    # -------------- MODELS VALIDATIONS ----------------

    @api.model
    def check_category_model(self):
        try:
            category_dict = {
                "id": 1,
                "keywords": [
                    "serveis",
                    "comer",
                    "instal·lacions"
                ],
                "code": "SC_EI_PR",
                "name": "Serveis de Comercialització - Estat instal·lacions - Procediment",
                "color": "#30C381",
                "enabled": True
            }
            cat_obj = Category.model_validate(category_dict)
            print(cat_obj)
        except ValidationError as e:
            print(e)

    @api.model
    def check_call_models(self):
        try:
            dict_test = {
                "operator": "operadora01",
                "call_timestamp": "2024-04-24T08:29:34.279876Z",
                "pbx_call_id": "35153",
                "phone_number": "625036666",
                "caller_erp_id": 666,
                "caller_name": "Pere",
                "caller_vat": "ES64006778D",
                "contract_erp_id": 12344,
                "contract_number": "5432100",
                "contract_address": "15, rue del percebe",
                "category_ids": [1, 2],
                "comments": "Està molt content amb nosaltres"
            }
            obj = NewCall.model_validate(dict_test)
            print(obj)

            dict_test['id'] = 5
            obj = Call.model_validate(dict_test)
            print(obj)

            dict_list_test = {'calls': [dict_test]}
            obj = CallLog.model_validate(dict_list_test)
            print(obj)

            dict_list_test['updated_id'] = 10
            obj = UpdatedCallLog.model_validate(dict_list_test)
            print(obj)

        except ValidationError as e:
            print(e)

    @api.model
    def check_pydantic_model(self):
        try:
            new_employee_dict = {
                "name": "juan",
                "email": "cdetuma@example.com",
                "date_of_birth": "1984-04-02",
                "salary": 30000.00,
                "department": "IT",
                "elected_benefits": True,
            }
            empl = Employee.model_validate(new_employee_dict)

            print("ok")
        except ValidationError as e:
            print(e)

    # -------------- ENDPOINTS ----------------

    @api.model
    def get_phonecall_categories_dummy(self):
        # Example date with timezone information
        iso_date_with_tz = "2024-03-20T12:00:00+03:00"
        # Convert ISO date string to datetime object
        dt_with_tz = datetime.fromisoformat(iso_date_with_tz)

        file_name = "dummy_pc_categories.json"
        file = get_module_resource(
            "odoo_callinfo", "json", file_name
        )
        with open(file, 'r') as f:
            data = json.load(f)
        return data

    @api.model
    def get_phonecall_categories(self):
        som_dummy = eval(self.env["ir.config_parameter"].sudo().get_param("som_callinfo_dummy", "False"))
        som_category_level = eval(
            self.env["ir.config_parameter"].sudo().get_param("som_callinfo_category_level", "3")
        )
        if som_dummy:
            res = self.get_phonecall_categories_dummy()
        else:
            cat_ids = self.env['product.category'].with_context(active_test=False).search([
                ('som_level', '=', som_category_level),
            ])
            res = {}
            cat_list = []
            for cat_id in cat_ids:
                color = cat_id._get_color_rgb(cat_id.som_family_color)['rgb']
                keywords = (
                    cat_id.with_context(lang="ca_ES").som_keyword_ids.mapped('name') if cat_id.som_keyword_ids else []
                )
                cat_dict = {
                    "id": cat_id.id,
                    "keywords": keywords,
                    "code": cat_id.som_full_code or '',
                    "name": cat_id.complete_name,
                    "color": color,
                    "enabled": cat_id.active,
                }
                cat_list.append(cat_dict)
            res['categories'] = cat_list
        try:
            Categories.model_validate(res)
            return res
        except ValidationError as e:
            return self._exception(e)

    def _get_calls(self):
        file_name = "dummy_pc.json"
        file = get_module_resource(
            "odoo_callinfo", "json", file_name
        )
        with open(file, 'r') as f:
            json_data = json.load(f)
        return json_data

    def _get_operator_calls(self, operator, calls_data):
        # Turn all calls into operator's
        # Temporary hack to be able to play with dummy
        return [
            dict(x, operator=operator)
            for x in calls_data["calls"]
        ]
        # Filter in operators call, legit code
        # return [
        #     x for x in calls_data["calls"]
        #     if x["operator"] == data["operator"]
        # ]

    def _exception(self, e):
        if isinstance(e, KeyError):
            error_msg = f"KeyError: {e}"
        else:
            error_msg = str(e)
        return {
            "error": error_msg,
        }

    @api.model
    def create_call_and_get_operator_calls(self, data):
        """
        sample param data expected:
        {'call_timestamp': '2024-03-20T12:00:00+03:00',
         'operator': 'operadora01',
         'pbx_call_id': '6265',
         'phone_number': '666444777'
        }
        """
        try:
            calls_data = self._get_calls()
            max_id = max([item["id"] for item in calls_data["calls"]])
            new_id = max_id + 1

            new_call = {
                "id": new_id,
                "operator": data["operator"],
                "call_timestamp": data["call_timestamp"],
                "pbx_call_id": data["pbx_call_id"],
                "phone_number": data["phone_number"],
                "caller_erp_id": data.get("caller_erp_id", False),
                "caller_vat": data.get("caller_vat", ""),
                "caller_name": data.get("caller_name", ""),
                "contract_erp_id": data.get('contract_erp_id', False),
                "contract_number": data.get("contract_number", ""),
                "contract_address": data.get("contract_address", ""),
                "category_ids": data.get("category_ids", []),
            }

            calls_data["calls"].append(new_call)
            calls = self._get_operator_calls(data["operator"], calls_data)
            res = {
                "updated_id": new_id,
                "calls": calls,
            }
            return res
        except Exception as e:
            return self._exception(e)

    @api.model
    def update_call_and_get_operator_calls(self, data):
        """
        sample param data expected:
        data = {
            "id": 1,
            "caller_erp_id": 16852,
            "caller_name": "Pere Garc",
            "caller_vat": "ES12345678Z",
            "contract_erp_id": 52613,
            "contract_number": "0026076",
            "contract_address": "C/ ALACANT, 76, 12 46680 (Algemesí)",
            "category_ids": [2, 3],
            "comments": "update test",
        }
        """
        try:
            calls_data = self._get_calls()
            call = list(filter(lambda x: x["id"] == data["id"], calls_data["calls"]))[0]
            for k, v in data.items():
                call[k] = v
            calls = self._get_operator_calls(data["operator"], calls_data)
            res = {
                "updated_id": call["id"],
                "calls": calls,
            }
            return res
        except Exception as e:
            return self._exception(e)

    @api.model
    def get_operator_calls(self, data):
        """
        sample param data expected:
        data = {
            "operator": "name",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "limit": 1000,
        }
        """
        try:
            calls_data = self._get_calls()
            calls = self._get_operator_calls(data["operator"], calls_data)
            res = {
                "calls": calls,
            }
            return res
        except Exception as e:
            return self._exception(e)