import json

from odoo.tests import common, tagged


def _json_headers(token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-API-Key'] = token
    return headers


class _ApiTestMixin:
    """Shared helpers for /api/v1/comm/log test classes."""

    def _post(self, payload: dict, token: str | None = 'test-token-123') -> dict:
        """POST JSON to the endpoint and parse the JSON response."""
        resp = self.url_open(
            '/api/v1/comm/log',
            data=json.dumps(payload),
            headers=_json_headers(token),
            timeout=30,
        )
        return resp.json()


@tagged('post_install', '-at_install')
class TestExternalLogApi(_ApiTestMixin, common.HttpCase):
    """End-to-end tests with a configured API token.

    The token is set in ``setUpClass`` (main transaction) so the HTTP
    handler's ``TestCursor`` (which wraps the same ``test_cr``) can
    see it.  Writing the token in ``setUp`` would put it inside a
    savepoint the HTTP handler cannot read.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'comm_log.api_token', 'test-token-123'
        )

    def setUp(self):
        super().setUp()
        self.partner = self.env.ref('base.res_partner_2')

    # ── Auth tests ─────────────────────────────────────────────────

    def test_auth_missing_token(self):
        """Request without token is rejected."""
        resp = self._post({'email': 'nobody@test.com'}, token=None)
        self.assertEqual(resp['status'], 'error')
        self.assertIn('Unauthorized', resp.get('message', ''))

    def test_auth_wrong_token(self):
        """Request with wrong token is rejected."""
        resp = self._post({'email': 'nobody@test.com'}, token='wrong-token')
        self.assertEqual(resp['status'], 'error')
        self.assertIn('Unauthorized', resp.get('message', ''))

    def test_auth_valid_token(self):
        """Valid token passes auth (fails later on missing partner)."""
        resp = self._post({'email': 'nobody@test.com'})
        self.assertEqual(resp['status'], 'error')
        self.assertIn('not found', resp.get('message', ''))

    # ── Validation tests ───────────────────────────────────────────

    def test_missing_email(self):
        """Missing email returns validation error."""
        resp = self._post({})
        self.assertEqual(resp['status'], 'error')
        self.assertIn('email', str(resp.get('errors', {})))

    def test_invalid_lang(self):
        """Unsupported language returns validation error."""
        resp = self._post({
            'email': self.partner.email,
            'lang': 'fr_FR',
        })
        self.assertEqual(resp['status'], 'error')
        self.assertIn('lang', str(resp.get('errors', {})))

    def test_valid_lang_accepted(self):
        """All supported languages pass validation."""
        for lang in ('es_ES', 'ca_ES', 'gl_ES', 'eu_ES'):
            resp = self._post({
                'email': self.partner.email,
                'lang': lang,
            })
            self.assertEqual(resp['status'], 'success', f'Failed for lang={lang}')

    # ── Success tests ──────────────────────────────────────────────

    def test_successful_log(self):
        """A valid request creates both mail.message and comm.log."""
        resp = self._post({
            'email': self.partner.email,
            'subject': 'Test API',
            'body_html': '<p>test</p>',
            'origin_app': 'mailchimp',
            'lang': 'ca_ES',
        })
        self.assertEqual(resp['status'], 'success')
        self.assertIn('message_id', resp)
        self.assertIn('comm_log_id', resp)

        log = self.env['comm.log'].browse(resp['comm_log_id'])
        self.assertTrue(log)
        self.assertEqual(log.partner_id, self.partner)
        self.assertEqual(log.source_type, 'external')
        self.assertEqual(log.origin_app, 'mailchimp')
        self.assertEqual(log.lang, 'ca_ES')

    def test_default_lang_on_missing(self):
        """Missing lang defaults to es_ES."""
        resp = self._post({'email': self.partner.email})
        self.assertEqual(resp['status'], 'success')
        log = self.env['comm.log'].browse(resp['comm_log_id'])
        self.assertEqual(log.lang, 'es_ES')

    def test_body_with_badge(self):
        """The response body shows the origin_app badge in comm.log."""
        resp = self._post({
            'email': self.partner.email,
            'body_html': '<p>content</p>',
            'origin_app': 'ov',
        })
        self.assertEqual(resp['status'], 'success')
        log = self.env['comm.log'].browse(resp['comm_log_id'])
        self.assertIn('Logged via OV', log.body_html)
        self.assertIn('<p>content</p>', log.body_html)


@tagged('post_install', '-at_install')
class TestExternalLogApiNoToken(_ApiTestMixin, common.HttpCase):
    """Test behaviour when no API token is configured.

    Lives in its own class because it must NOT set a token in
    setUpClass.  The ``TestCursor`` wraps the shared ``test_cr``
    transaction, so any uncommitted token written there would be
    visible to the HTTP handler, making this test fail.
    """

    def test_auth_not_configured(self):
        """No API token → reject all requests with an auth error.

        Sends **no** ``X-API-Key`` header so the test works regardless
        of whether the token is set in the database:
        ``not configured`` (no token in DB) or ``Unauthorized``
        (token present but header missing) — both are fine.
        """
        resp = self._post({'email': 'nobody@test.com'}, token=None)
        self.assertEqual(resp['status'], 'error')
        self.assertIn(resp.get('message', ''), (
            'API token not configured on server',
            'Unauthorized',
        ), f'Expected auth error, got: {resp.get("message", "")}')
