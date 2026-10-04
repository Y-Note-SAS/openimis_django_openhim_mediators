from django.test import TestCase

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
                "Claim", urn="urn:x", version="1.0.0", name="N", description="D", **kwargs
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

    def test_custom_methods_and_url_pattern(self):
        conf = self._register(
            methods=("GET", "PATCH"), url_pattern="^/p(/[^/]+)?$"
        ).call_args.kwargs["conf"]
        channel = conf["defaultChannelConfig"][0]
        self.assertEqual(channel["urlPattern"], "^/p(/[^/]+)?$")
        self.assertEqual(channel["methods"], ["GET", "PATCH"])
