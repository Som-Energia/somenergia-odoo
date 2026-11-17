from odoo.tests import HttpCase, new_test_user, no_retry, tagged

from odoo.addons.web.tests.test_js import qunit_error_checker


@tagged("post_install", "-at_install")
class TestContractLookupAction(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="lookup_js_agent", password="lookup_js_agent",
            groups="base.group_user,helpdesk_mgmt.group_helpdesk_user",
        )

    @no_retry
    def test_link_partner_to_call(self):
        self.browser_js(
            "/web/tests?mod=helpdesk_contract_lookup&filter=Contract%20Lookup%20Linking",
            "",
            login=self.agent.login,
            timeout=180,
            error_checker=qunit_error_checker,
        )
