/** @odoo-module **/

import { DiscussContainer } from "@mail/components/discuss_container/discuss_container";
import { registry } from "@web/core/registry";

class WhatsappDiscussContainer extends DiscussContainer {
    setup() {
        super.setup();
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(async () => {
            await this.messaging.initializedPromise;
            this.discuss.openInitThread();
        });
    }
}

registry.category("actions").add("som_whatsapp.action_discuss", WhatsappDiscussContainer);
