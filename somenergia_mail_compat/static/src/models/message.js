/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "Message",
    fields: {
        isDiscussionOrNotification: {
            compute() {
                if (this.message_type === "auto_comment") {
                    return true;
                }
                return this._super();
            },
        },
        messageTypeText: {
            compute() {
                if (this.message_type === "auto_comment") {
                    return this.env._t("Automated message");
                }
                return this._super();
            },
        },
    },
});
