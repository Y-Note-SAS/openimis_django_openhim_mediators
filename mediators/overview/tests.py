from django.test import TestCase

from overview.fhir_proxy import MEDIATOR_VERSION
from overview.models import configs
from overview.views import configview


CONFIG_FIELDS = {
    "openimis_url": "http://openimis.local",
    "openhim_url": "openhim.local",
    "mediator_url": "mediator.local",
    "openhim_user": "openhim-admin",
    "openhim_passkey": "openhim-secret",
    "openimis_user": "admin",
    "openimis_passkey": "secret",
    "openimis_port": 8080,
    "openhim_port": 8080,
    "mediator_port": 8000,
}


class ConfigsModelTests(TestCase):
    def test_str_returns_openimis_url(self):
        config = configs.objects.create(**CONFIG_FIELDS)
        self.assertEqual(str(config), CONFIG_FIELDS["openimis_url"])

    def test_save_enforces_single_instance(self):
        first = configs.objects.create(**CONFIG_FIELDS)

        other_fields = dict(CONFIG_FIELDS, openimis_url="http://changed.local")
        second = configs(**other_fields)
        second.save()

        self.assertEqual(configs.objects.count(), 1)
        stored = configs.objects.first()
        self.assertEqual(stored.pk, first.pk)
        self.assertEqual(stored.openimis_url, "http://changed.local")


class ConfigviewTests(TestCase):
    def test_returns_serialized_config_when_present(self):
        configs.objects.create(**CONFIG_FIELDS)

        response = configview()

        self.assertEqual(response.data["openimis_url"], CONFIG_FIELDS["openimis_url"])
        self.assertEqual(response.data["openimis_port"], CONFIG_FIELDS["openimis_port"])

    def test_returns_empty_data_when_no_config_exists(self):
        response = configview()

        self.assertIsNone(response.data.get("id"))


class RegisterFhirMediatorTests(TestCase):
    """register_fhir_mediator builds the openHIM conf and starts the heartbeat."""

    def _register(self, **kwargs):
        from unittest.mock import patch
        from overview.fhir_proxy import register_fhir_mediator

        with patch("overview.fhir_proxy.configview") as cfg, patch(
            "overview.fhir_proxy.Main"
        ) as main:
            cfg.return_value.__dict__["data"] = CONFIG_FIELDS
            register_fhir_mediator(
                "Claim", urn="urn:x", **kwargs
            )
        return main

    def test_registers_and_activates_heartbeat(self):
        main = self._register()
        instance = main.return_value
        instance.register_mediator.assert_called_once_with()
        instance.activate_heartbeat.assert_called_once_with()

    def test_builds_default_conf_from_resource(self):
        conf = self._register().call_args.kwargs["conf"]
        channel = conf["defaultChannelConfig"][0]
        self.assertEqual(channel["urlPattern"], "^/api/api_fhir_r4/Claim$")
        self.assertEqual(channel["methods"], ["GET", "POST"])
        self.assertEqual(channel["routes"][0]["path"], "/api/api_fhir_r4/Claim")
        self.assertEqual(channel["routes"][0]["host"], "mediator.local")
        self.assertEqual(conf["urn"], "urn:x")
        self.assertEqual(conf["version"], MEDIATOR_VERSION)
        self.assertEqual(conf["name"], "openIMIS Fhir R4 Claim Mediator")
        self.assertEqual(conf["description"], conf["name"])
        self.assertEqual(channel["name"], conf["name"])

    def test_custom_methods_and_url_pattern(self):
        conf = self._register(
            methods=("GET", "PATCH"), url_pattern="^/p(/[^/]+)?$"
        ).call_args.kwargs["conf"]
        channel = conf["defaultChannelConfig"][0]
        self.assertEqual(channel["urlPattern"], "^/p(/[^/]+)?$")
        self.assertEqual(channel["methods"], ["GET", "PATCH"])


class ProxyGetByIdTests(TestCase):
    """proxy_fhir_request reads a single resource when an id is given."""

    def _get(self, resource_id=None, trailing_slash=False, query=None):
        import json
        from unittest.mock import MagicMock, patch
        from rest_framework.test import APIRequestFactory
        from overview.fhir_proxy import proxy_fhir_request

        upstream = MagicMock(status_code=200, text=json.dumps({"id": "c-1"}))
        request = APIRequestFactory().get("/x", query or {})
        from rest_framework.request import Request
        with patch("overview.fhir_proxy.configview") as cfg, patch(
            "overview.fhir_proxy.requests.request", return_value=upstream
        ) as mock_request:
            cfg.return_value.__dict__["data"] = CONFIG_FIELDS
            response = proxy_fhir_request(
                Request(request), "Claim", resource_id, trailing_slash=trailing_slash
            )
        return response, mock_request

    def test_get_with_id_reads_single_resource(self):
        response, mock_request = self._get(resource_id="c-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_request.call_args[0][1],
            "http://openimis.local:8080/api/api_fhir_r4/Claim/c-1/",
        )

    def test_get_with_id_and_trailing_slash_does_not_double_slash(self):
        _, mock_request = self._get(resource_id="c-1", trailing_slash=True)
        self.assertEqual(
            mock_request.call_args[0][1],
            "http://openimis.local:8080/api/api_fhir_r4/Claim/c-1/",
        )

    def test_get_without_id_keeps_list_url(self):
        _, mock_request = self._get()
        self.assertEqual(
            mock_request.call_args[0][1],
            "http://openimis.local:8080/api/api_fhir_r4/Claim",
        )


class RegisterFhirMediatorOptionsTests(RegisterFhirMediatorTests):
    """display_name and id-aware routes of register_fhir_mediator."""

    def test_display_name_overrides_resource_in_name(self):
        conf = self._register(display_name="Diagnosis").call_args.kwargs["conf"]
        self.assertEqual(conf["name"], "openIMIS Fhir R4 Diagnosis Mediator")
        self.assertEqual(conf["description"], conf["name"])

    def test_default_pattern_keeps_route_path(self):
        conf = self._register().call_args.kwargs["conf"]
        route = conf["defaultChannelConfig"][0]["routes"][0]
        self.assertEqual(route["path"], "/api/api_fhir_r4/Claim")

    def test_custom_pattern_route_forwards_original_path(self):
        conf = self._register(url_pattern="^/p(/[^/]+)?$").call_args.kwargs["conf"]
        route = conf["defaultChannelConfig"][0]["routes"][0]
        self.assertNotIn("path", route)
