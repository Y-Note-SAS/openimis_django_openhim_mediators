import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from group_mediator.views import getGroup

FAKE_CONFIG_DATA = {
    "openimis_url": "http://openimis.local",
    "openimis_port": 8080,
    "openimis_user": "admin",
    "openimis_passkey": "secret",
    "openhim_url": "openhim.local",
    "openhim_port": 8080,
    "openhim_user": "openhim-admin",
    "openhim_passkey": "openhim-secret",
    "mediator_url": "mediator.local",
    "mediator_port": 8000,
}


class FakeConfigResult:
    """Mimics the DRF Response object returned by overview.views.configview.

    getGroup reads it via result.__dict__["data"], so only a "data"
    attribute needs to be set for the tests to reproduce that access pattern.
    """

    def __init__(self, data):
        self.data = data


def fake_upstream_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.text = json.dumps(payload if payload is not None else {})
    return response


class GetGroupTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.config_patcher = patch(
            "group_mediator.views.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        self.mock_configview = self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    def test_get_forwards_request_and_returns_upstream_data(self):
        expected_payload = {"resourceType": "Bundle", "entry": []}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(200, expected_payload),
        ) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/Group")
            response = getGroup(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(
            args[1], "http://openimis.local:8080/api/api_fhir_r4/Group"
        )
        self.assertIn("Authorization", kwargs["headers"])
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_ignores_search_query_params(self):
        # Documents current behavior: getGroup hardcodes an empty querystring,
        # so a search like ?identifier=123 is silently dropped and the full
        # list is requested instead. See patient_mediator for the fixed version.
        expected_payload = {"resourceType": "Bundle", "entry": []}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(200, expected_payload),
        ) as mock_request:
            request = self.factory.get(
                "/api/api_fhir_r4/Group", {"identifier": "123"}
            )
            getGroup(request)

        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"": ""})

    def test_post_forwards_request_body_and_returns_upstream_data(self):
        posted_group = {"resourceType": "Group", "id": "123"}
        expected_payload = {"resourceType": "Group", "id": "123", "created": True}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(201, expected_payload),
        ) as mock_request:
            request = self.factory.post(
                "/api/api_fhir_r4/Group", posted_group, format="json"
            )
            response = getGroup(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(json.loads(kwargs["data"]), posted_group)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIn("Authorization", kwargs["headers"])

    def test_get_does_not_propagate_upstream_error_status(self):
        # Documents current behavior: the upstream status code (e.g. 404) is
        # not propagated, the mediator always answers 200.
        error_payload = {"error": "not found"}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(404, error_payload),
        ):
            request = self.factory.get("/api/api_fhir_r4/Group")
            response = getGroup(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, error_payload)

    def test_unsupported_method_returns_405(self):
        with patch("group_mediator.views.requests.request") as mock_request:
            request = self.factory.delete("/api/api_fhir_r4/Group")
            response = getGroup(request)

        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 405)
