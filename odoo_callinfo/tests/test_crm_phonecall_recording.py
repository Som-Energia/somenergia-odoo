# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


MOCK_TOKEN = 'fake-token-abc123'
MOCK_CALL_ID = '0000000000.00000'
MOCK_BASE_URL = 'https://pbx.example.com'
MOCK_INTERNAL_HOST = 'https://192.168.1.1'
MOCK_RECORDING_PATH = '/ivozng/recorder/download.php?op=download&id=1'
MOCK_RECORDING_URL = f'{MOCK_INTERNAL_HOST}{MOCK_RECORDING_PATH}'
MOCK_PUBLIC_URL = f'{MOCK_BASE_URL}{MOCK_RECORDING_PATH}'


def _make_response(status_code, json_data):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def _make_error_response(status_code):
    import requests
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock
    )
    return mock


@tagged('som_callinfo_recording')
class TestActionDownloadRecording(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PhoneCall = cls.env['crm.phonecall']

        cls.phonecall = cls.PhoneCall.create({
            'name': 'Test call',
            'direction': 'in',
            'som_pbx_call_id': MOCK_CALL_ID,
        })

        cls.phonecall_no_pbx_id = cls.PhoneCall.create({
            'name': 'Call without PBX id',
            'direction': 'in',
        })

    def _patch_config(self):
        config_values = {
            'irontec_base_url': MOCK_BASE_URL,
            'irontec_api_user': 'user@example.com',
            'irontec_api_pwd': 'secret',
        }
        mock_config = MagicMock()
        mock_config.get = config_values.get
        return patch(
            'odoo.addons.odoo_callinfo.models.crm_phonecall.config',
            new=mock_config,
        )

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.get')
    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_download_recording_returns_act_url(self, mock_post, mock_get):
        """Happy path: returns act_url with public URL."""
        mock_post.return_value = _make_response(200, {'token': MOCK_TOKEN})
        mock_get.return_value = _make_response(200, {'url': MOCK_RECORDING_URL})

        with self._patch_config():
            result = self.phonecall.action_download_recording()

        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertEqual(result['url'], MOCK_PUBLIC_URL)

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.get')
    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_login_called_with_credentials(self, mock_post, mock_get):
        """Login is called with the configured credentials."""
        mock_post.return_value = _make_response(200, {'token': MOCK_TOKEN})
        mock_get.return_value = _make_response(200, {'url': MOCK_RECORDING_URL})

        with self._patch_config():
            self.phonecall.action_download_recording()

        mock_post.assert_called_once_with(
            f'{MOCK_BASE_URL}/ApiRest/index.php/api/login',
            json={'username': 'user@example.com', 'password': 'secret'},
            timeout=10,
        )

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.get')
    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_get_records_called_with_token_and_call_id(self, mock_post, mock_get):
        """getRecords is called with Bearer token and correct call ID."""
        mock_post.return_value = _make_response(200, {'token': MOCK_TOKEN})
        mock_get.return_value = _make_response(200, {'url': MOCK_RECORDING_URL})

        with self._patch_config():
            self.phonecall.action_download_recording()

        mock_get.assert_called_once_with(
            f'{MOCK_BASE_URL}/ApiRest/index.php/api/custom/getRecords/{MOCK_CALL_ID}',
            headers={'Authorization': f'Bearer {MOCK_TOKEN}'},
            timeout=10,
        )

    def test_raises_if_no_pbx_call_id(self):
        """UserError if the call has no som_pbx_call_id."""
        with self.assertRaises(UserError):
            self.phonecall_no_pbx_id.action_download_recording()

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_raises_if_missing_config(self, mock_post):
        """UserError if credentials are missing from config."""
        mock_config = MagicMock()
        mock_config.get = lambda key, default=None: None
        with patch(
            'odoo.addons.odoo_callinfo.models.crm_phonecall.config',
            new=mock_config,
        ):
            with self.assertRaises(UserError):
                self.phonecall.action_download_recording()

        mock_post.assert_not_called()

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_raises_on_login_http_error(self, mock_post):
        """UserError if login returns HTTP error."""
        mock_post.return_value = _make_error_response(401)

        with self._patch_config():
            with self.assertRaises(UserError):
                self.phonecall.action_download_recording()

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.get')
    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_raises_if_token_missing_in_response(self, mock_post, mock_get):
        """UserError if login succeeds but response has no token."""
        mock_post.return_value = _make_response(200, {})

        with self._patch_config():
            with self.assertRaises(UserError):
                self.phonecall.action_download_recording()

        mock_get.assert_not_called()

    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.get')
    @patch('odoo.addons.odoo_callinfo.models.crm_phonecall.requests.post')
    def test_raises_on_get_records_http_error(self, mock_post, mock_get):
        """UserError if getRecords returns HTTP error."""
        mock_post.return_value = _make_response(200, {'token': MOCK_TOKEN})
        mock_get.return_value = _make_error_response(404)

        with self._patch_config():
            with self.assertRaises(UserError):
                self.phonecall.action_download_recording()
