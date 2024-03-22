# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from odoo.modules.module import get_module_resource
from datetime import datetime, timezone, timedelta
import json


class CrmPhonecall(models.Model):
    _inherit = 'crm.phonecall'

    @api.model
    def get_phonecall_categories(self, include_disabled=False):
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

        if include_disabled:
            return data
        else:
            data_filtered = list(filter(lambda x: x.get("enabled", False), data["categories"]))
            return data_filtered

    def _get_calls(self):
        file_name = "dummy_pc.json"
        file = get_module_resource(
            "odoo_callinfo", "json", file_name
        )
        with open(file, 'r') as f:
            json_data = json.load(f)
        return json_data

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
                "caller_erp_id": False,
                "caller_name": "",
                "contract_erp_id": "",
                "contract_number": "",
                "contract_address": "",
                "category_ids": [],
            }

            calls_data["calls"].append(new_call)
            calls = list(filter(lambda x: x["operator"] == data["operator"], calls_data["calls"]))
            res = {
                "odoo_id": new_id,
                "operator_calls": calls,
            }
            return res
        except Exception as e:
            return self._exception(e)

    @api.model
    def update_call_and_get_operator_calls(self, data):
        """
        sample param data expected:
        data = {
            "odoo_id": 1,
            "caller_erp_id": 16852,
            "caller_name": "Pere Garc",
            "contract_erp_id": 52613,
            "contract_number": "0026076",
            "contract_address": "C/ ALACANT, 76, 12 46680 (Algemesí)",
            "category_ids": [2, 3],
            "comments": "update test",
        }
        """
        try:
            calls_data = self._get_calls()
            call = list(filter(lambda x: x["id"] == data["odoo_id"], calls_data["calls"]))[0]
            for k, v in data.items():
                cv = call[k]
                call[k] = v
            calls = list(filter(lambda x: x["operator"] == call["operator"], calls_data["calls"]))
            res = {
                "odoo_id": call["id"],
                "operator_calls": calls,
            }
            return res
        except Exception as e:
            return self._exception(e)
