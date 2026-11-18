from unittest.mock import patch

from odoo.addons.base_rest.models.rest_service_registration import (
    RestServiceRegistration,
)
from odoo.tests.common import TransactionCase


class TestRestRoutingCache(TransactionCase):
    def test_build_invalidates_all_cached_routing_maps(self):
        http_model = type(self.env["ir.http"])
        cached_maps = {None: object(), 42: object()}
        with patch.object(http_model, "_routing_map", cached_maps, create=True):
            self.env["rest.service.registration"]._build_controllers_routes({})
            self.assertEqual(http_model._routing_map, {})

    def test_invalidation_follows_generation_and_preserves_result(self):
        registration = self.env["rest.service.registration"]
        http_model = type(self.env["ir.http"])
        cached_maps = {None: object()}
        services = {"/compat-test/": object()}
        expected_result = object()

        def generate(record, services_registry):
            self.assertEqual(record, registration)
            self.assertIs(services_registry, services)
            # Existing maps must remain available until generation finishes.
            self.assertIs(http_model._routing_map, cached_maps)
            return expected_result

        with patch.object(http_model, "_routing_map", cached_maps, create=True), patch.object(
            RestServiceRegistration, "_build_controllers_routes", generate
        ):
            result = registration._build_controllers_routes(services)
            self.assertIs(result, expected_result)
            self.assertEqual(http_model._routing_map, {})

    def test_failed_generation_propagates_without_clearing_maps(self):
        http_model = type(self.env["ir.http"])
        cached_maps = {None: object()}
        with patch.object(http_model, "_routing_map", cached_maps, create=True), patch.object(
            RestServiceRegistration,
            "_build_controllers_routes",
            side_effect=RuntimeError("Controller generation failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Controller generation failed"):
                self.env["rest.service.registration"]._build_controllers_routes({})
            self.assertIs(http_model._routing_map, cached_maps)
