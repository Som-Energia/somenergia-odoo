SomEnergia Base REST Compatibility
==================================

Refresh Odoo's HTTP routing cache after ``base_rest`` generates its controllers.
This prevents REST endpoints from returning HTTP 404 when an earlier HTTP
request cached a routing map before those controllers existed.

Installation
------------

Install ``somenergia_base_rest_compat`` explicitly alongside your REST addons::

    python src/core/odoo-bin -c "$ODOO_CONFIG" -d "$ODOO_DATABASE" \
      -i somenergia_base_rest_compat --stop-after-init

For a fresh database, include this addon in the existing installation list.
It depends only on ``base_rest``; no Helpdesk or core source changes are needed.
It is independent of ``somenergia_mail_compat``.

Behavior and scope
------------------

The addon extends ``rest.service.registration._build_controllers_routes`` and
clears all HTTP routing maps after successful controller generation. The next
HTTP request rebuilds them using the registered controllers. This covers both
normal registry initialization and the explicit REST registry setup used by
the upstream tests.

No routes, authentication settings, request data or database records are
changed. Exceptions and return values from controller generation are preserved.
Invalidation occurs on controller registration, not on every HTTP request.

Validation
----------

Run the addon tests and the original HTTP regression together::

    python src/core/odoo-bin -c "$ODOO_CONFIG" -d "$ODOO_DATABASE" \
      --test-tags=/somenergia_base_rest_compat,/som_crm:TestCRMLeadAPIHttp,/helpdesk_ticket_api \
      --stop-after-init --max-cron-threads=0

The addon tests cover cached-map invalidation, ordering, return values and
exception propagation. The combined CRM/Helpdesk tests exercise the original
HTTP failure: an early CRM request followed by dynamic REST registration and
ticket API requests. These integration tests require the corresponding addons
and their demo fixtures to be installed.

Removal
-------

Keep this addon until the deployed ``base_rest`` or core handles routing cache
invalidation after dynamic controller registration. Before removing it, verify
the combined HTTP regression above against the target versions. No data
migration is needed; uninstalling removes the cache-invalidation override.
