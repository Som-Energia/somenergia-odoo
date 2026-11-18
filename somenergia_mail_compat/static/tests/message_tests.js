/** @odoo-module **/

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("somenergia_mail_compat", {}, function () {
    QUnit.test("auto comments are displayed as automated messages", async function (assert) {
        const { messaging } = await start();
        const message = messaging.models.Message.insert({
            id: 10001,
            message_type: "auto_comment",
        });
        assert.strictEqual(message.isDiscussionOrNotification, true);
        assert.strictEqual(message.messageTypeText, "Automated message");
    });

    QUnit.test("internal notes keep their original presentation", async function (assert) {
        const { messaging } = await start();
        const message = messaging.models.Message.insert({
            id: 10002,
            message_type: "comment",
            is_note: true,
        });
        assert.strictEqual(message.isDiscussionOrNotification, false);
        assert.strictEqual(message.messageTypeText, "Note");
        message.update({ message_type: "notification" });
        assert.strictEqual(message.messageTypeText, "System notification");
    });
});
