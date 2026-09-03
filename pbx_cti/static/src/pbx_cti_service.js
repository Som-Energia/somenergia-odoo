/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const pbxCtiService = {
    dependencies: ["bus_service", "action", "notification"],

    start(env, { bus_service, action, notification }) {
        const uid = session.user_id;
        bus_service.addChannel(`pbx_cti_${uid}`);

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "pbx_incoming_call") {
                    const openLookup = () => {
                        action.doAction(
                            {
                                type: "ir.actions.client",
                                tag: "helpdesk_contract_lookup.main",
                                name: "Contacte 360",
                                params: {
                                    field: "phone",
                                    value: payload.phone,
                                    auto_search: true,
                                    phonecall_id: payload.phonecall_id,
                                    call_info: {
                                        phone: payload.phone,
                                        callid: payload.callid,
                                        created_at: payload.created_at,
                                    },
                                },
                            },
                            { stackPosition: "push" }
                        );
                    };

                    if (document.visibilityState === "visible") {
                        const closeNotif = notification.add(
                            `Incoming call: ${payload.phone}`,
                            {
                                type: "warning",
                                sticky: true,
                                buttons: [
                                    {
                                        name: "Open Lookup",
                                        primary: true,
                                        onClick: () => {
                                            closeNotif();
                                            openLookup();
                                        },
                                    },
                                ],
                            }
                        );
                    }
                }
            }
        });
    },
};

registry.category("services").add("pbxCti", pbxCtiService);
