/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ContractLookupAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        const initialField = this.fields.includes(params.field) ? params.field : "phone";
        const initialValue = (params.value || "").toString();
        this.phonecallId = params.phonecall_id || null;
        this.state = useState({
            field: initialField,
            value: initialValue,
            loading: false,
            error: "",
            result: null,
            detailsByContract: {},
            loadingDetailsByContract: {},
            linkedPartnerId: null,
        });
        onWillStart(async () => {
            if (params.auto_search && this.state.value.trim()) {
                await this.onSearch();
            }
        });
    }

    get fields() {
        return ["phone", "name", "nif", "soci", "email", "contract", "cups", "all"];
    }

    async onSearch() {
        this.state.loading = true;
        this.state.error = "";
        this.state.result = null;
        this.state.detailsByContract = {};
        try {
            const result = await this._rpcSearch();
            this.state.result = result;
        } catch (error) {
            this.state.error = error.message || "Unexpected search error.";
            this.notification.add(this.state.error, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async onSearchKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        ev.preventDefault();
        await this.onSearch();
    }

    async _rpcSearch() {
        return this.rpc("/helpdesk_contract_lookup/search", {
            field: this.state.field,
            value: this.state.value,
            limit: 20,
        });
    }

    async linkPartnerToCall(partnerId, partnerName, partnerVat) {
        try {
            await this.rpc("/helpdesk_contract_lookup/link_partner_to_call", {
                phonecall_id: this.phonecallId,
                partner_id: partnerId,
                partner_name: partnerName,
                partner_vat: partnerVat,
            });
            this.notification.add(
                `Partner "${partnerName}" linked to call.`,
                { type: "success" }
            );
            this.state.linkedPartnerId = partnerId;
        } catch (error) {
            const message = error.message || "Unexpected error linking partner to call.";
            this.notification.add(message, { type: "danger" });
        }
    }

    async linkPartnerToCallAndOpen(partnerId, partnerName, partnerVat) {
        await this.linkPartnerToCall(partnerId, partnerName, partnerVat);
        this.openPhonecall();
    }

    openPhonecall() {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "crm.phonecall",
                res_id: this.phonecallId,
                views: [[false, "form"]],
                target: "current",
            },
            { newWindow: true }
        );
    }

    async loadContractDetails(contractNumber) {
        if (!contractNumber) {
            return;
        }
        if (this.state.detailsByContract[contractNumber]) {
            return;
        }
        this.state.loadingDetailsByContract[contractNumber] = true;
        try {
            const response = await this.rpc("/helpdesk_contract_lookup/contract_details", {
                contract_numbers: [contractNumber],
            });
            this.state.detailsByContract[contractNumber] = response.contracts[contractNumber] || {
                invoices: [],
                atr_cases: [],
                meter_readings: [],
            };
        } catch (error) {
            const message = error.message || "Unexpected details error.";
            this.notification.add(message, { type: "danger" });
        } finally {
            this.state.loadingDetailsByContract[contractNumber] = false;
        }
    }
}

ContractLookupAction.template = "helpdesk_contract_lookup.ContractLookupAction";

registry.category("actions").add("helpdesk_contract_lookup.main", ContractLookupAction);
