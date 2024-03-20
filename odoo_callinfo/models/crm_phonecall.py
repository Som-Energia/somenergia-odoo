# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from odoo.modules.module import get_module_resource
from datetime import datetime, timezone, timedelta
import json


class CrmPhonecall(models.Model):
    _inherit = 'crm.phonecall'

    def get_phonecall_categories(self):
        # Example date with timezone information
        iso_date_with_tz = "2024-03-20T12:00:00+03:00"

        # Convert ISO date string to datetime object
        dt_with_tz = datetime.fromisoformat(iso_date_with_tz)

        file_name = "dummy_pc_categories.json"
        file = get_module_resource(
            "odoo_callinfo", "json", file_name
        )
        with open(file, 'r') as f:
            json_data = json.load(f)

        for dict_item in json_data:
            dict_item["date"] = dt_with_tz.isoformat()
        return json.dumps(json_data, sort_keys=True)

    def _get_calls(self):
        file_name = "dummy_pc.json"
        file = get_module_resource(
            "odoo_callinfo", "json", file_name
        )
        with open(file, 'r') as f:
            json_data = json.load(f)
        return json_data

    def create_call_and_get_operator_calls(self, operator, call_timestamp, pbx_call_id, phone_number):
        json_data = self._get_calls()

        max_id = max([item["id"] for item in json_data])
        new_id = max_id + 1

        new_call = {
            "id": new_id,
            "operator": operator,
            "call_timestamp": call_timestamp,
            "pbx_call_id": pbx_call_id,
            "phone_number": phone_number,
            "caller_erp_id": False,
            "caller_name": "",
            "contract_erp_id": "",
            "contract_number": "",
            "contract_address": "",
            "category_ids": [],
        }
        json_data.append(new_call)
        calls = list(filter(lambda x: x["operator"] == operator, json_data))
        res = {
            "odoo_id": new_id,
            "operator_calls": calls,
        }
        return json.dumps(res, sort_keys=True)

    def update_call_and_get_operator_calls(self, dict_data):
        # dict_data = {
        #     "odoo_id": 1,
        #     "caller_erp_id": 16852,
        #     "caller_name": "Pere Montagud",
        #     "contract_erp_id": 52613,
        #     "contract_number": "0026076",
        #     "contract_address": "C/ ALBALAT, 42, 12 46680 (Algemesí)",
        #     "category_ids": [2, 3],
        #     "comments": "update test",
        # }
        json_data = self._get_calls()
        call = list(filter(lambda x: x["id"] == dict_data["odoo_id"], json_data))[0]
        for k, v in dict_data.items():
            call[k] = v
        calls = list(filter(lambda x: x["operator"] == call["operator"], json_data))
        res = {
            "odoo_id": call["id"],
            "operator_calls": calls,
        }
        return json.dumps(res, sort_keys=True)

    def get_operator_calls(self, operator):
        pass
