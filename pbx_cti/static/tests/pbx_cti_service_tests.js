/** @odoo-module **/

import { pbxCtiService } from "@pbx_cti/pbx_cti_service";
import { session } from "@web/session";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";

QUnit.module("PBX CTI", (hooks) => {
    let bus;
    let channels;
    let notifications;
    let actions;
    let closedNotifications;

    const payload = {
        phone: "900123456",
        callid: "test-pbx-call",
        phonecall_id: 123,
        created_at: "10:30:00",
    };

    hooks.beforeEach(async () => {
        await startServer();
        patchWithCleanup(session, { uid: 42, user_id: undefined });
        patchWithCleanup(document, {
            get visibilityState() {
                return "visible";
            },
        });
        channels = [];
        notifications = [];
        actions = [];
        closedNotifications = 0;
        bus = new EventTarget();
        bus.addChannel = (channel) => channels.push(channel);
        pbxCtiService.start({}, {
            bus_service: bus,
            action: {
                doAction: (action, options) => actions.push({ action, options }),
            },
            notification: {
                add(message, options) {
                    notifications.push({ message, options });
                    return () => closedNotifications++;
                },
            },
        });
    });

    function receive(type) {
        bus.dispatchEvent(new CustomEvent("notification", {
            detail: [{ type, payload }],
        }));
    }

    QUnit.test("subscribes to the signed-in user's server channel", (assert) => {
        assert.deepEqual(channels, ["pbx_cti_42"]);
    });

    QUnit.test("incoming call shows a notification and opens the matching lookup", (assert) => {
        receive("pbx_incoming_call");
        assert.strictEqual(notifications.length, 1);
        assert.strictEqual(notifications[0].message, "Incoming call: 900123456");
        assert.strictEqual(notifications[0].options.type, "warning");
        assert.strictEqual(notifications[0].options.sticky, true);
        assert.strictEqual(actions.length, 0, "Receiving a call does not navigate automatically");

        notifications[0].options.buttons[0].onClick();

        assert.strictEqual(closedNotifications, 1);
        assert.strictEqual(actions.length, 1);
        assert.strictEqual(actions[0].action.type, "ir.actions.client");
        assert.strictEqual(actions[0].action.tag, "helpdesk_contract_lookup.main");
        assert.deepEqual(actions[0].action.params, {
            field: "phone",
            value: payload.phone,
            auto_search: true,
            phonecall_id: payload.phonecall_id,
            call_info: {
                phone: payload.phone,
                callid: payload.callid,
                created_at: payload.created_at,
            },
        });
        assert.deepEqual(actions[0].options, { stackPosition: "push" });
    });

    QUnit.test("unrelated bus notifications are ignored", (assert) => {
        receive("unrelated_notification");
        assert.strictEqual(notifications.length, 0);
        assert.strictEqual(actions.length, 0);
    });

    QUnit.test("hidden tabs do not show duplicate call notifications", (assert) => {
        patchWithCleanup(document, {
            get visibilityState() {
                return "hidden";
            },
        });
        receive("pbx_incoming_call");
        assert.strictEqual(notifications.length, 0);
        assert.strictEqual(actions.length, 0);
    });
});
