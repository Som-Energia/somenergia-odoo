import base64
import json
import gspread
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class GsheetsConnector(models.Model):
    _name = 'gsheets.connector'
    _description = 'Connector Google Sheets'

    name = fields.Char(string='Task name', required=True)
    google_sheet_id = fields.Char(
        string='Google Sheet ID',
        required=True,
        help="ID from the Google Sheet (the part of the URL after /d/ and before /edit)")
    worksheet_name = fields.Char(
        string='Worksheet Name',
        default='Sheet1',
        help="Name of the worksheet within the Google Sheet (default is 'Sheet1')")

    # field to upload the JSON credentials file
    credentials_json = fields.Binary(string='JSON file (Service Account)')
    credentials_filename = fields.Char(string='Filename')

    def get_data_from_google_sheet(self):
        self.ensure_one()

        # 1. Decode the uploaded JSON file
        try:
            json_data = base64.b64decode(self.credentials_json).decode('utf-8')
            credentials_dict = json.loads(json_data)
        except Exception as e:
            logger.error("Error reading the JSON file: %s", e)
            return False

        # 2. Connect to Google Sheets using gspread
        try:
            gc = gspread.service_account_from_dict(credentials_dict)
            sh = gc.open_by_key(self.google_sheet_id)
            worksheet = sh.worksheet(self.worksheet_name)

            # Get all records (returns a list of dictionaries)
            records = worksheet.get_all_records()
            return records
        except Exception as e:
            logger.error("Error connecting to Google: %s", e)
            return False

    def test_connection(self):
        self.ensure_one()

        res = self.get_data_from_google_sheet()
        if not res:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _(
                        'Failed to connect to the Google Sheet. \n'
                        'Please check your credentials and sheet details.'),
                    'sticky': True,
                }
            }
        else:
            # If we reach here, the connection is successful
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _(
                        'Successfully connected to the Google Sheet and data has been read.\n'
                        'Number of records retrieved: %d' % len(res)),
                    'sticky': False,
                }
            }
