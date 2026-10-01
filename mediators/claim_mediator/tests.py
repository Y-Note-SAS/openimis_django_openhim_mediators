import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from claim_mediator.views import getClaims

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

BASE_URL = "http://openimis.local:8080/api/api_fhir_r4/Claim/"
REQUESTS_PATH = "claim_mediator.views.requests.request"


class FakeConfigResult:
    """Mimics the DRF Response object returned by overview.views.configview.

    getClaims reads it via result.__dict__["data"], so only a "data"
    attribute needs to be set for the tests to reproduce that access pattern.
    """

    def __init__(self, data):
        self.data = data


def fake_upstream_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.text = json.dumps(payload if payload is not None else {})
    return response


def broken_upstream_response(status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.text = "<html>not json</html>"
    return response


class GetClaimsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.config_patcher = patch(
            "claim_mediator.views.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        self.mock_configview = self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    # ------------------------------------------------------------------
    # GET (liste)
    # ------------------------------------------------------------------
    def test_get_list_forwards_request_and_returns_upstream_data(self):
        expected_payload = {"resourceType": "Bundle", "entry": []}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/Claim")
            response = getClaims(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(kwargs["params"], {})
        self.assertIn("Authorization", kwargs["headers"])
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_search_forwards_query_params(self):
        expected_payload = {"resourceType": "Bundle", "entry": [{"id": "c-1"}]}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get(
                "/api/api_fhir_r4/Claim", {"patient": "Patient/123"}
            )
            response = getClaims(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        args, kwargs = mock_request.call_args
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(kwargs["params"], {"patient": "Patient/123"})

    def test_get_list_propagates_upstream_error_payload(self):
        error_payload = {"error": "server error"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(500, error_payload)
        ):
            request = self.factory.get("/api/api_fhir_r4/Claim")
            response = getClaims(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, error_payload)

    def test_get_list_returns_502_when_upstream_body_is_not_json(self):
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/Claim")
            response = getClaims(request)

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # GET par identifiant
    # ------------------------------------------------------------------
    def test_get_by_id_forwards_id_and_returns_upstream_data(self):
        expected_payload = {"resourceType": "Claim", "id": "c-1"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/Claim/c-1")
            response = getClaims(request, resource_id="c-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], BASE_URL + "c-1/")
        self.assertEqual(kwargs["params"], {})
        self.assertIn("Authorization", kwargs["headers"])

    def test_get_by_unknown_id_propagates_404(self):
        error_payload = {
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found"}],
        }
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(404, error_payload)
        ):
            request = self.factory.get("/api/api_fhir_r4/Claim/unknown")
            response = getClaims(request, resource_id="unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_payload)

    def test_get_by_id_returns_502_when_upstream_body_is_not_json(self):
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/Claim/c-1")
            response = getClaims(request, resource_id="c-1")

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------
    def test_post_forwards_request_body_and_returns_upstream_data(self):
        posted_claim = {"resourceType": "Claim", "status": "active"}
        expected_payload = {"resourceType": "Claim", "id": "c-1", "status": "active"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(201, expected_payload)
        ) as mock_request:
            request = self.factory.post(
                "/api/api_fhir_r4/Claim", posted_claim, format="json"
            )
            response = getClaims(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(json.loads(kwargs["data"]), posted_claim)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIn("Authorization", kwargs["headers"])

    def test_post_propagates_upstream_error_payload(self):
        error_payload = {"error": "invalid claim"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(400, error_payload)
        ):
            request = self.factory.post(
                "/api/api_fhir_r4/Claim", {"resourceType": "Claim"}, format="json"
            )
            response = getClaims(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, error_payload)

    def test_post_returns_502_when_upstream_body_is_not_json(self):
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(201)):
            request = self.factory.post(
                "/api/api_fhir_r4/Claim", {"resourceType": "Claim"}, format="json"
            )
            response = getClaims(request)

        self.assertEqual(response.status_code, 502)

    def test_post_with_resource_id_returns_405(self):
        with patch(REQUESTS_PATH) as mock_request:
            request = self.factory.post(
                "/api/api_fhir_r4/Claim/c-1", {"resourceType": "Claim"}, format="json"
            )
            response = getClaims(request, resource_id="c-1")

        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 405)

    # ------------------------------------------------------------------
    # PATCH
    # ------------------------------------------------------------------
    def test_patch_forwards_request_body_and_returns_upstream_data(self):
        patch_body = {
            "resourceType": "Claim",
            "billablePeriod": {"start": "2026-09-29", "end": "2026-09-30"},
        }
        expected_payload = {"resourceType": "Claim", "id": "c-1", **patch_body}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.patch(
                "/api/api_fhir_r4/Claim/c-1", patch_body, format="json"
            )
            response = getClaims(request, resource_id="c-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "PATCH")
        self.assertEqual(args[1], BASE_URL + "c-1/")
        self.assertEqual(json.loads(kwargs["data"]), patch_body)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIn("Authorization", kwargs["headers"])

    def test_patch_without_resource_id_returns_400(self):
        with patch(REQUESTS_PATH) as mock_request:
            request = self.factory.patch(
                "/api/api_fhir_r4/Claim", {"status": "cancelled"}, format="json"
            )
            response = getClaims(request)

        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 400)

    def test_patch_on_unknown_id_propagates_404(self):
        error_payload = {"error": "claim not found"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(404, error_payload)
        ):
            request = self.factory.patch(
                "/api/api_fhir_r4/Claim/unknown", {"status": "cancelled"}, format="json"
            )
            response = getClaims(request, resource_id="unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_payload)

    def test_patch_propagates_upstream_error_payload(self):
        error_payload = {"error": "invalid claim patch"}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(400, error_payload)
        ):
            request = self.factory.patch(
                "/api/api_fhir_r4/Claim/c-1", {"status": "cancelled"}, format="json"
            )
            response = getClaims(request, resource_id="c-1")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, error_payload)

    def test_patch_returns_502_when_upstream_body_is_not_json(self):
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.patch(
                "/api/api_fhir_r4/Claim/c-1", {"status": "cancelled"}, format="json"
            )
            response = getClaims(request, resource_id="c-1")

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # Méthodes non supportées
    # ------------------------------------------------------------------
    def test_unsupported_methods_return_405(self):
        for method in ("delete", "put"):
            with self.subTest(method=method):
                with patch(REQUESTS_PATH) as mock_request:
                    request = getattr(self.factory, method)(
                        "/api/api_fhir_r4/Claim/c-1", {}, format="json"
                    )
                    response = getClaims(request, resource_id="c-1")

                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 405)
