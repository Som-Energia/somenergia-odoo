from odoo.addons.web.tests.test_js import qunit_error_checker
from odoo.tests import HttpCase, no_retry, tagged


@tagged("post_install", "-at_install")
class TestAutoCommentDisplay(HttpCase):
    @no_retry
    def test_auto_comment_display(self):
        self.browser_js(
            "/web/tests?mod=somenergia_mail_compat&filter=somenergia_mail_compat",
            "",
            login="admin",
            timeout=90,
            error_checker=qunit_error_checker,
        )
