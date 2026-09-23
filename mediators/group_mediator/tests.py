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
            args[1], "http://openimis.local:8080/api/api_fhir_r4/Group/"
        )
        self.assertEqual(kwargs["params"], {})
        self.assertIn("Authorization", kwargs["headers"])
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_search_by_identifier_forwards_query_params(self):
        expected_payload = {"resourceType": "Bundle", "entry": [{"id": "123"}]}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(200, expected_payload),
        ) as mock_request:
            request = self.factory.get(
                "/api/api_fhir_r4/Group", {"identifier": "123"}
            )
            response = getGroup(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"identifier": "123"})

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

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(json.loads(kwargs["data"]), posted_group)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIn("Authorization", kwargs["headers"])

    def test_post_propagates_upstream_error_payload(self):
        error_payload = {"error": "invalid group"}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(400, error_payload),
        ):
            request = self.factory.post(
                "/api/api_fhir_r4/Group", {"resourceType": "Group"}, format="json"
            )
            response = getGroup(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, error_payload)

    def test_post_returns_502_when_upstream_body_is_not_json(self):
        broken_response = MagicMock()
        broken_response.status_code = 201
        broken_response.text = "<html>not json</html>"
        with patch(
            "group_mediator.views.requests.request",
            return_value=broken_response,
        ):
            request = self.factory.post(
                "/api/api_fhir_r4/Group", {"resourceType": "Group"}, format="json"
            )
            response = getGroup(request)

        self.assertEqual(response.status_code, 502)

    def test_get_propagates_upstream_error_payload(self):
        error_payload = {"error": "not found"}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(404, error_payload),
        ):
            request = self.factory.get("/api/api_fhir_r4/Group")
            response = getGroup(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_payload)

    def test_get_returns_502_when_upstream_body_is_not_json(self):
        broken_response = MagicMock()
        broken_response.status_code = 200
        broken_response.text = "<html>not json</html>"
        with patch(
            "group_mediator.views.requests.request",
            return_value=broken_response,
        ):
            request = self.factory.get("/api/api_fhir_r4/Group")
            response = getGroup(request)

        self.assertEqual(response.status_code, 502)

    def test_unsupported_method_returns_405(self):
        with patch("group_mediator.views.requests.request") as mock_request:
            request = self.factory.delete("/api/api_fhir_r4/Group")
            response = getGroup(request)

        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 405)

    def test_patch_forwards_request_body_and_returns_upstream_data(self):
        patch_body = {"resourceType": "Group", "active": False}
        expected_payload = {"resourceType": "Group", "id": "123", "active": False}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(200, expected_payload),
        ) as mock_request:
            request = self.factory.patch(
                "/api/api_fhir_r4/Group/123", patch_body, format="json"
            )
            response = getGroup(request, resource_id="123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "PATCH")
        self.assertEqual(
            args[1], "http://openimis.local:8080/api/api_fhir_r4/Group/123/"
        )
        self.assertEqual(json.loads(kwargs["data"]), patch_body)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIn("Authorization", kwargs["headers"])

    def test_patch_without_resource_id_returns_400(self):
        with patch("group_mediator.views.requests.request") as mock_request:
            request = self.factory.patch(
                "/api/api_fhir_r4/Group", {"active": False}, format="json"
            )
            response = getGroup(request)

        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 400)

    def test_patch_propagates_upstream_error_payload(self):
        error_payload = {"error": "invalid group patch"}
        with patch(
            "group_mediator.views.requests.request",
            return_value=fake_upstream_response(400, error_payload),
        ):
            request = self.factory.patch(
                "/api/api_fhir_r4/Group/123", {"active": False}, format="json"
            )
            response = getGroup(request, resource_id="123")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, error_payload)

    def test_patch_returns_502_when_upstream_body_is_not_json(self):
        broken_response = MagicMock()
        broken_response.status_code = 200
        broken_response.text = "<html>not json</html>"
        with patch(
            "group_mediator.views.requests.request",
            return_value=broken_response,
        ):
            request = self.factory.patch(
                "/api/api_fhir_r4/Group/123", {"active": False}, format="json"
            )
            response = getGroup(request, resource_id="123")

        self.assertEqual(response.status_code, 502)
