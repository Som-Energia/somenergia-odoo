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
        this.phonecallId = params.phonecall_id ? parseInt(params.phonecall_id, 10) : null;
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
            linkedContractNumber: null,
            phonecallsByPartner: {},
            loadingPhonecallsByPartner: {},
        });
        onWillStart(async () => {
            if (this.state.value.trim()) {
                await this.onSearch();
            }
        });
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
        this.state.phonecallsByPartner = {};
        this.state.loadingPhonecallsByPartner = {};
        try {
            const result = await this._rpcSearch();
            this.state.result = result;
            // Auto-load phonecalls for all found partners (fire and forget)
            if (result && result.partners) {
                for (const partner of result.partners) {
                    this.loadPartnerPhonecalls(partner.id);
                }
            }
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

    async linkPartnerToCall(partnerId, partnerName, partnerVat, contractName) {
        try {
            await this.rpc("/helpdesk_contract_lookup/link_partner_to_call", {
                phonecall_id: this.phonecallId,
                partner_id: partnerId,
                partner_name: partnerName,
                partner_vat: partnerVat,
                contract_name: contractName || null,
            });
            const label = contractName
                ? `Partner "${partnerName}" / Contract "${contractName}" linked to call.`
                : `Partner "${partnerName}" linked to call.`;
            this.notification.add(label, { type: "success" });
            this.state.linkedPartnerId = partnerId;
            this.state.linkedContractNumber = contractName || null;
            this._reloadAllPhonecalls();
        } catch (error) {
            const message = error.message || "Unexpected error linking partner to call.";
            this.notification.add(message, { type: "danger" });
        }
    }

    _reloadAllPhonecalls() {
        const partners = (this.state.result && this.state.result.partners) || [];
        for (const partner of partners) {
            const pid = partner.id;
            if (!pid) continue;
            delete this.state.phonecallsByPartner[pid];
            this.loadPartnerPhonecalls(pid);
        }
    }

    async linkPartnerToCallAndOpen(partnerId, partnerName, partnerVat, contractName) {
        await this.linkPartnerToCall(partnerId, partnerName, partnerVat, contractName);
        this.openPhonecall(partnerId);
    }

    async openPartnerInOdoo(partnerId, partnerName, partnerVat) {
        try {
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
                    target: "new",
                },
                {
                    onClose: () => {
                        delete this.state.phonecallsByPartner[partnerId];
                        this.loadPartnerPhonecalls(partnerId);
                    },
                }
            );
        } catch (error) {
            const message = error.message || "Unexpected error opening partner in Odoo.";
            this.notification.add(message, { type: "danger" });
        }
    }

    async registerIncomingCall(partnerId, partnerName, partnerVat, partnerPhone) {
        try {
            const response = await this.rpc("/helpdesk_contract_lookup/register_incoming_call", {
                partner_id: partnerId,
                partner_name: partnerName,
                partner_vat: partnerVat,
                partner_phone: partnerPhone,
            });
            this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "crm.phonecall",
                    res_id: response.phonecall_id,
                    views: [[false, "form"]],
                    target: "new",
                },
                {
                    onClose: () => {
                        delete this.state.phonecallsByPartner[partnerId];
                        this.loadPartnerPhonecalls(partnerId);
                    },
                }
            );
        } catch (error) {
            const message = error.message || "Unexpected error registering incoming call.";
            this.notification.add(message, { type: "danger" });
        }
    }

    openPhonecall(partnerId = null) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "crm.phonecall",
                res_id: this.phonecallId,
                views: [[false, "form"]],
                target: "new",
            },
            partnerId ? {
                onClose: () => {
                    delete this.state.phonecallsByPartner[partnerId];
                    this.loadPartnerPhonecalls(partnerId);
                },
            } : {}
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

    async loadPartnerPhonecalls(partnerId) {
        if (!partnerId || typeof partnerId !== "number") return;
        // Skip if already loaded or currently loading
        if (
            this.state.phonecallsByPartner[partnerId] !== undefined ||
            this.state.loadingPhonecallsByPartner[partnerId]
        ) {
            return;
        }
        this.state.loadingPhonecallsByPartner[partnerId] = true;
        try {
            const response = await this.rpc("/helpdesk_contract_lookup/partner_phonecalls", {
                partner_id: partnerId,
            });
            this.state.phonecallsByPartner[partnerId] = {
                phonecalls: response.phonecalls || [],
                odoo_partner_found: response.odoo_partner_found,
            };
        } catch (error) {
            const message = error.message || "Unexpected error loading phone calls.";
            this.notification.add(message, { type: "danger" });
        } finally {
            this.state.loadingPhonecallsByPartner[partnerId] = false;
        }
    }

    openCall(callId, partnerId) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "crm.phonecall",
                res_id: callId,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: () => {
                    delete this.state.phonecallsByPartner[partnerId];
                    this.loadPartnerPhonecalls(partnerId);
                },
            }
        );
    }

    callStateBadge(state) {
        if (state === "open") return "badge bg-warning text-dark";
        if (state === "done") return "badge bg-success";
        if (state === "cancel") return "badge bg-danger";
        if (state === "pending") return "badge bg-info text-dark";
        return "badge bg-secondary";
    }

    callStateLabel(state) {
        if (state === "open") return "Confirmed";
        if (state === "done") return "Held";
        if (state === "cancel") return "Cancelled";
        if (state === "pending") return "Pending";
        return state || "—";
    }

    callDirectionIcon(direction) {
        if (direction === "in") return "fa fa-arrow-down text-primary";
        if (direction === "out") return "fa fa-arrow-up text-success";
        return "fa fa-phone";
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
