from odoo import models


class RestServiceRegistration(models.AbstractModel):
    _inherit = "rest.service.registration"

    def _build_controllers_routes(self, services_registry):
        result = super()._build_controllers_routes(services_registry)
        # Earlier HTTP requests may have cached a map without these controllers.
        # Cover both registry hooks and explicit REST registry rebuilds in tests.
        self.env["ir.http"]._clear_routing_map()
        return result
