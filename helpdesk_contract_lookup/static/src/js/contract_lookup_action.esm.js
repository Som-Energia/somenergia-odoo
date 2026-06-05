/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ContractLookupAction extends Component {
    get storageKey() {
        return "helpdesk_contract_lookup.return_search";
    }

    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        const savedSearch = this._consumeSavedSearch();
        const initialField = this.fields.includes(params.field)
            ? params.field
            : (savedSearch && this.fields.includes(savedSearch.field) ? savedSearch.field : "phone");
        const initialValue = (params.value || savedSearch?.value || "").toString();
        this.phonecallId = params.phonecall_id || null;
        this.callInfo = params.call_info || null;
        this.state = useState({
            field: initialField,
            value: initialValue,
            loading: false,
            error: "",
            result: null,
            detailsByContract: {},
            loadingDetailsByContract: {},
            expandedContracts: {},
            activeTabByContract: {},
            linkedPartnerId: null,
        });
        onWillStart(async () => {
            if (this.state.value.trim()) {
                await this.onSearch();
            }
        });
    }

    _consumeSavedSearch() {
        try {
            const raw = sessionStorage.getItem(this.storageKey);
            if (!raw) {
                return null;
            }
            sessionStorage.removeItem(this.storageKey);
            return JSON.parse(raw);
        } catch {
            sessionStorage.removeItem(this.storageKey);
            return null;
        }
    }

    _saveReturnSearch() {
        try {
            sessionStorage.setItem(this.storageKey, JSON.stringify({
                field: this.state.field,
                value: this.state.value,
            }));
        } catch {
            // Ignore storage failures.
        }
    }

    get fields() {
        return ["phone", "name", "nif", "soci", "email", "contract", "cups", "partner_id", "all"];
    }

    get fieldLabels() {
        return {
            phone: "Phone",
            name: "Name",
            nif: "NIF",
            soci: "Member code",
            email: "Email",
            contract: "Contract",
            cups: "CUPS",
            partner_id: "Partner ID",
            all: "All",
        };
    }

    async onSearch() {
        this.state.loading = true;
        this.state.error = "";
        this.state.result = null;
        this.state.detailsByContract = {};
        this.state.expandedContracts = {};
        this.state.activeTabByContract = {};
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

    async openPartnerInOdoo(partnerId, partnerName, partnerVat) {
        try {
            this._saveReturnSearch();
            const response = await this.rpc("/helpdesk_contract_lookup/open_partner_in_odoo", {
                partner_id: partnerId,
                partner_name: partnerName,
                partner_vat: partnerVat,
            });
            this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "res.partner",
                    res_id: response.odoo_partner_id,
                    views: [[false, "form"]],
                    target: "current",
                },
                { stackPosition: "push" }
            );
        } catch (error) {
            const message = error.message || "Unexpected error opening partner in Odoo.";
            this.notification.add(message, { type: "danger" });
        }
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

    atrStateBadge(state) {
        if (state === 'open') return 'badge bg-warning text-dark';
        if (state === 'done') return 'badge bg-success';
        if (state === 'cancel') return 'badge bg-danger';
        return 'badge bg-secondary';
    }

    getActiveTab(contractNumber) {
        return this.state.activeTabByContract[contractNumber] || "invoices";
    }

    setActiveTab(contractNumber, tab) {
        this.state.activeTabByContract[contractNumber] = tab;
    }

    invoiceStateBadge(state) {
        if (state === 'open') return 'badge bg-warning text-dark';
        if (state === 'paid') return 'badge bg-success';
        if (state === 'cancel') return 'badge bg-danger';
        return 'badge bg-secondary';
    }

    invoiceStateIcon(state) {
        if (state === 'open') return 'fa fa-clock-o';
        if (state === 'paid') return 'fa fa-check';
        if (state === 'cancel') return 'fa fa-times';
        return 'fa fa-question';
    }

    invoiceStateLabel(state) {
        if (state === 'open') return 'Open';
        if (state === 'paid') return 'Paid';
        if (state === 'cancel') return 'Cancelled';
        return state || '—';
    }

    async loadContractDetails(contractNumber) {
        if (!contractNumber) {
            return;
        }
        // If already loaded, just toggle visibility
        if (this.state.detailsByContract[contractNumber]) {
            this.state.expandedContracts[contractNumber] = !this.state.expandedContracts[contractNumber];
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
            this.state.expandedContracts[contractNumber] = true;
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
