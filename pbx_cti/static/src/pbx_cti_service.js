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
                        type: "ir.actions.act_window",
                        res_model: payload.res_model,
                        res_id: payload.res_id,
                        views: [[false, "form"]],
                        target: "new",
                    });
                }
            }
        });
    },
};

registry.category("services").add("pbxCti", pbxCtiService);
