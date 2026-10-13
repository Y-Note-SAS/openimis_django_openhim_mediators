import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from medication_mediator.views import getMedication

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

PATH = "/api/api_fhir_r4/Medication"
UPSTREAM = "http://openimis.local:8080" + PATH + "/"


class FakeConfigResult:
    """Mimics the DRF Response returned by overview.views.configview."""

    def __init__(self, data):
        self.data = data


def fake_upstream_response(status_code=200, payload=None, text=None):
    response = MagicMock()
    response.status_code = status_code
    response.text = text if text is not None else json.dumps(
        payload if payload is not None else {}
    )
    return response


class getMedicationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        patcher = patch(
            "overview.fhir_proxy.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get(self, upstream, resource_id=None, query=None):
        with patch(
            "overview.fhir_proxy.requests.request", return_value=upstream
        ) as mock_request:
            url = PATH + ("/" + resource_id if resource_id else "")
            request = self.factory.get(url, query or {})
            response = getMedication(request, resource_id=resource_id)
        return response, mock_request

    def test_get_list_forwards_request_and_returns_upstream_data(self):
        """GET liste : appelle /Medication/ sur openIMIS et relaie sa réponse."""
        payload = {"resourceType": "Bundle", "entry": []}
        response, mock_request = self._get(fake_upstream_response(200, payload))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, payload)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], UPSTREAM)
        self.assertEqual(kwargs["params"], {})
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_search_forwards_query_params(self):
        """Les paramètres de recherche FHIR sont transmis tels quels."""
        _, mock_request = self._get(
            fake_upstream_response(200, {}), query={"code": "X1", "_count": "10"}
        )
        self.assertEqual(mock_request.call_args[1]["params"], {"code": "X1", "_count": "10"})

    def test_get_list_propagates_upstream_error_status(self):
        """Une erreur d'openIMIS est relayée avec son code HTTP et son corps."""
        error = {"detail": "Authentication credentials were not provided."}
        response, _ = self._get(fake_upstream_response(401, error))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, error)

    def test_get_list_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502."""
        response, _ = self._get(fake_upstream_response(200, text="<html>not json</html>"))
        self.assertEqual(response.status_code, 502)

    def test_get_by_id_reads_single_resource(self):
        """GET /Medication/<id> appelle /Medication/<id>/ sur openIMIS."""
        payload = {"resourceType": "Medication", "id": "r-1"}
        response, mock_request = self._get(fake_upstream_response(200, payload), "r-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, payload)
        self.assertEqual(mock_request.call_args[0][1], UPSTREAM + "r-1/")
        self.assertEqual(mock_request.call_args[1]["params"], {})

    def test_get_by_unknown_id_propagates_404(self):
        """Un identifiant inconnu : le 404 d'openIMIS est relayé tel quel."""
        error = {"resourceType": "OperationOutcome", "issue": [{"code": "not-found"}]}
        response, _ = self._get(fake_upstream_response(404, error), "unknown")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error)

    def test_get_by_id_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502, même par identifiant."""
        response, _ = self._get(fake_upstream_response(200, text="not json"), "r-1")
        self.assertEqual(response.status_code, 502)

    def test_unsupported_methods_return_405(self):
        """POST, PUT, PATCH et DELETE renvoient 405 sans appeler openIMIS."""
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                with patch("overview.fhir_proxy.requests.request") as mock_request:
                    request = getattr(self.factory, method)(PATH + "/r-1", {}, format="json")
                    response = getMedication(request, resource_id="r-1")
                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 405)
