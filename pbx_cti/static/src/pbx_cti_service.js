/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const pbxCtiService = {
    dependencies: ["bus_service", "action"],

    start(env, { bus_service, action }) {
        const uid = session.user_id;
        bus_service.addChannel(`pbx_cti_${uid}`);

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "pbx_incoming_call") {
                    action.doAction({
                        type: "ir.actions.client",
                        tag: "helpdesk_contract_lookup.main",
                        params: {
                            field: "phone",
                            value: payload.phone,
                            auto_search: true,
                        },
                    });
                }
            }
        });
    },
};

registry.category("services").add("pbxCti", pbxCtiService);
