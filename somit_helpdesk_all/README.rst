Som Energia Helpdesk deployment
================================

Install the selected Helpdesk addons and the compatibility bridges required
by Som Energia's pinned Odoo 16 environment with ``somit_helpdesk_all``.
This module only declares dependencies; it adds no models or application data.

Installation
------------

Make this repository and the external addon repositories available through
``addons_path``, then install the aggregator::

    python src/core/odoo-bin -c "$ODOO_CONFIG" -d "$ODOO_DATABASE" \
      -i somit_helpdesk_all --stop-after-init

The dependencies include the selected 29 external addons, plus:

* ``somenergia_mail_compat`` for the missing mail APIs and ``auto_comment``.
* ``somenergia_base_rest_compat`` for dynamic REST routing cache invalidation.

The intentionally excluded addons are ``helpdesk_dynamic_custom_fields``,
``helpdesk_ticket_to_lead_outbound`` and ``helpdesk_ticket_track_fetchmail_fix``.
The latter addresses a defect absent from the deployed ``helpdesk_mgmt``.
The bridges are maintained here rather than in third-party repositories.

Relocation and upgrades
------------------------

The aggregator was relocated from the external ``odoo-helpdesk`` checkout to
``somenergia-odoo``. Its technical name remains ``somit_helpdesk_all``, so an
existing installation does not need a rename migration or reinstallation.

Keep only one copy of the addon on ``addons_path``. Remove the old addon source
directory from the external checkout when deploying this relocation, restart
Odoo and update the installed aggregator to load the added dependencies::

    python src/core/odoo-bin -c "$ODOO_CONFIG" -d "$ODOO_DATABASE" \
      -u somit_helpdesk_all --stop-after-init

Do not uninstall the aggregator as part of the relocation.

Attribution
-----------

The original SomIt aggregator is attributed to Som IT Cooperatiu SCCL and
licensed under AGPL-3. The deployment-specific dependency selection and
compatibility integration are maintained by Som Energia SCCL.

Original repository: https://gitlab.com/somitcoop/erp-research/odoo-helpdesk
