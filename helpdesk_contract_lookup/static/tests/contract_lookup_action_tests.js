/** @odoo-module **/

import "@helpdesk_contract_lookup/js/contract_lookup_action.esm";
import { registry } from "@web/core/registry";
import { makeDeferred } from "@web/../tests/helpers/utils";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";

QUnit.module("Contract Lookup Linking", (hooks) => {
    let lookup;
    let actions;
    let notifications;
    let reloads;

    hooks.beforeEach(async () => {
        await startServer();
        const LookupAction = registry.category("actions").get("helpdesk_contract_lookup.main");
        lookup = Object.create(LookupAction.prototype);
        actions = [];
        notifications = [];
        reloads = 0;
        Object.assign(lookup, {
            phonecallId: 123,
            phonecallFormViewId: 456,
            state: { linkedPartnerId: 7, linkedContractNumber: "Previous contract" },
            rpc: async () => ({ status: "ok" }),
            action: { doAction: (action) => actions.push(action) },
            notification: { add: (message, options) => notifications.push({ message, options }) },
            _reloadAllPhonecalls: () => reloads++,
        });
    });

    QUnit.test("search leaves the limit to the backend configuration", async (assert) => {
        assert.expect(3);
        lookup.state.field = "name";
        lookup.state.value = "Example";
        const result = { status: "no_info", partners: [], limit: 7 };
        lookup.rpc = async (route, params) => {
            assert.strictEqual(route, "/helpdesk_contract_lookup/search");
            assert.deepEqual(params, { field: "name", value: "Example" });
            return result;
        };

        assert.strictEqual(await lookup._rpcSearch(), result);
    });

    QUnit.test("failed linking does not open the call or change the linked partner", async (assert) => {
        lookup.rpc = async () => {
            throw new Error("Link rejected");
        };

        await lookup.linkPartnerToCallAndOpen(42, "Example", false, "C005");

        assert.strictEqual(actions.length, 0);
        assert.strictEqual(lookup.state.linkedPartnerId, 7);
        assert.strictEqual(lookup.state.linkedContractNumber, "Previous contract");
        assert.strictEqual(reloads, 0);
        assert.deepEqual(notifications, [{ message: "Link rejected", options: { type: "danger" } }]);
    });

    QUnit.test("successful linking opens the call only after the RPC completes", async (assert) => {
        const deferred = makeDeferred();
        lookup.rpc = (route, params) => {
            assert.strictEqual(route, "/helpdesk_contract_lookup/link_partner_to_call");
            assert.deepEqual(params, {
                phonecall_id: 123,
                partner_id: 42,
                partner_name: "Example",
                partner_vat: false,
                contract_name: "C005",
            });
            return deferred;
        };

        const linking = lookup.linkPartnerToCallAndOpen(42, "Example", false, "C005");
        assert.strictEqual(actions.length, 0, "The call stays closed while linking is pending");
        deferred.resolve({ status: "ok" });
        await linking;

        assert.strictEqual(actions.length, 1);
        assert.deepEqual(actions[0], {
            type: "ir.actions.act_window",
            res_model: "crm.phonecall",
            res_id: 123,
            views: [[456, "form"]],
            target: "new",
        });
        assert.strictEqual(lookup.state.linkedPartnerId, 42);
        assert.strictEqual(lookup.state.linkedContractNumber, "C005");
        assert.strictEqual(reloads, 1);
        assert.strictEqual(notifications[0].options.type, "success");
    });

    QUnit.test("standalone linking returns true without opening the call", async (assert) => {
        const linked = await lookup.linkPartnerToCall(42, "Example", false);

        assert.strictEqual(linked, true);
        assert.strictEqual(actions.length, 0);
        assert.strictEqual(lookup.state.linkedContractNumber, null);
        assert.strictEqual(reloads, 1);
    });

    QUnit.test("standalone linking returns false without an unhandled rejection", async (assert) => {
        lookup.rpc = async () => {
            throw new Error();
        };

        const linked = await lookup.linkPartnerToCall(42, "Example", false);

        assert.strictEqual(linked, false);
        assert.strictEqual(actions.length, 0);
        assert.strictEqual(reloads, 0);
        assert.deepEqual(notifications, [{
            message: "Unexpected error linking partner to call.",
            options: { type: "danger" },
        }]);
    });
});
