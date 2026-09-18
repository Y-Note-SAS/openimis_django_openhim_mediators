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
