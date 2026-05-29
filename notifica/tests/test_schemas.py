from odoo.tests import common

from ..schemas import (
    CommLogCreateRequest,
    CommLogCreateResponse,
    ApiErrorResponse,
)
from ..config import SUPPORTED_LANG_KEYS, ORIGIN_APP_DEFAULT


class TestCommLogCreateRequest(common.TransactionCase):
    """Validate CommLogCreateRequest Pydantic model."""

    def test_valid_request(self):
        """A valid payload passes without errors."""
        data = CommLogCreateRequest(
            email='test@example.com',
            subject='Hello',
            body_html='<p>Hi</p>',
            origin_app='mailchimp',
            lang='es_ES',
        ).model_dump()
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['lang'], 'es_ES')

    def test_default_values(self):
        """Omitting optional fields applies defaults."""
        data = CommLogCreateRequest(email='a@b.com').model_dump()
        self.assertEqual(data['subject'], 'External Communication')
        self.assertEqual(data['origin_app'], ORIGIN_APP_DEFAULT)
        self.assertEqual(data['lang'], 'es_ES')
        self.assertEqual(data['body_html'], '')

    def test_lang_valid_all(self):
        """All 4 supported languages are accepted."""
        for lang in SUPPORTED_LANG_KEYS:
            data = CommLogCreateRequest(email='a@b.com', lang=lang).model_dump()
            self.assertEqual(data['lang'], lang)

    def test_lang_invalid(self):
        """An unsupported language raises ValueError."""
        with self.assertRaises(Exception):
            CommLogCreateRequest(email='a@b.com', lang='fr_FR')

    def test_email_required(self):
        """email is a required field."""
        with self.assertRaises(Exception):
            CommLogCreateRequest()

    def test_api_key_not_in_schema(self):
        """api_key is not a business field — must be sent via X-API-Key header."""
        data = CommLogCreateRequest(email='a@b.com').model_dump()
        self.assertNotIn('api_key', data)


class TestApiErrorResponse(common.TransactionCase):
    """Validate ApiErrorResponse Pydantic model."""

    def test_error_with_message(self):
        resp = ApiErrorResponse(status='error', message='Something wrong').model_dump(exclude_none=True)
        self.assertEqual(resp['status'], 'error')
        self.assertEqual(resp['message'], 'Something wrong')
        self.assertNotIn('errors', resp)

    def test_error_with_errors(self):
        resp = ApiErrorResponse(
            status='error',
            message='Validation failed',
            errors={'email': 'field required'},
        ).model_dump(exclude_none=True)
        self.assertEqual(resp['errors'], {'email': 'field required'})


class TestCommLogCreateResponse(common.TransactionCase):
    """Validate CommLogCreateResponse extends ApiErrorResponse."""

    def test_success_response(self):
        resp = CommLogCreateResponse(
            status='success',
            message_id=42,
            comm_log_id=99,
        ).model_dump(exclude_none=True)
        self.assertEqual(resp['status'], 'success')
        self.assertEqual(resp['message_id'], 42)
        self.assertEqual(resp['comm_log_id'], 99)
        self.assertNotIn('message', resp)

    def test_inherits_error_fields(self):
        """CommLogCreateResponse can also carry error fields from parent."""
        resp = CommLogCreateResponse(
            status='error', message='fail', errors={'x': 'y'},
        ).model_dump(exclude_none=True)
        self.assertEqual(resp['message'], 'fail')
        self.assertEqual(resp['errors'], {'x': 'y'})

    def test_is_subclass(self):
        self.assertTrue(issubclass(CommLogCreateResponse, ApiErrorResponse))
