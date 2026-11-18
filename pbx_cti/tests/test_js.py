from odoo.tests import HttpCase, new_test_user, no_retry, tagged

from odoo.addons.web.tests.test_js import qunit_error_checker


@tagged("post_install", "-at_install")
class TestPbxCtiService(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="pbx_js_agent", password="pbx_js_agent", groups="base.group_user",
        )

    @no_retry
    def test_pbx_cti_service(self):
        self.browser_js(
            "/web/tests?mod=pbx_cti&filter=PBX%20CTI",
            "",
            login=self.agent.login,
            timeout=180,
            error_checker=qunit_error_checker,
        )
