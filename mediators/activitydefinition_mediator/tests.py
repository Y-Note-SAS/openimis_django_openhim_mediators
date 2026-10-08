import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from activitydefinition_mediator.views import getActivityDefinition

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

BASE_URL = "http://openimis.local:8080/api/api_fhir_r4/ActivityDefinition/"
REQUESTS_PATH = "activitydefinition_mediator.views.requests.request"
RESOURCE_ID = "82c9773f-a174-4f7e-beb8-747172705cd2"


class FakeConfigResult:
    """Imite la réponse DRF renvoyée par overview.views.configview.

    getActivityDefinition la lit via result.__dict__["data"] : seul l'attribut "data"
    est donc nécessaire pour reproduire ce mode d'accès dans les tests.
    """

    def __init__(self, data):
        self.data = data


def fake_upstream_response(status_code=200, payload=None):
    """Construit une fausse réponse d'openIMIS dont le corps est du JSON."""
    response = MagicMock()
    response.status_code = status_code
    response.text = json.dumps(payload if payload is not None else {})
    return response


def broken_upstream_response(status_code=200):
    """Construit une fausse réponse d'openIMIS dont le corps n'est pas du JSON."""
    response = MagicMock()
    response.status_code = status_code
    response.text = "<html>not json</html>"
    return response


class GetActivityDefinitionTests(TestCase):
    def setUp(self):
        """Prépare la fabrique de requêtes et remplace la configuration par des valeurs factices."""
        self.factory = APIRequestFactory()
        self.config_patcher = patch(
            "activitydefinition_mediator.views.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        self.mock_configview = self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    # ------------------------------------------------------------------
    # GET liste
    # ------------------------------------------------------------------
    def test_get_list_forwards_request_and_returns_upstream_data(self):
        """Le GET liste appelle /ActivityDefinition/ sur openIMIS et renvoie sa réponse."""
        expected_payload = {"resourceType": "Bundle", "entry": []}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition")
            response = getActivityDefinition(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(kwargs["params"], {})
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_search_forwards_query_params(self):
        """Les paramètres de recherche FHIR sont transmis tels quels à openIMIS."""
        expected_payload = {"resourceType": "Bundle", "entry": [{"id": RESOURCE_ID}]}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get(
                "/api/api_fhir_r4/ActivityDefinition", {"code": "PCS13", "_count": "10"}
            )
            response = getActivityDefinition(request)

        self.assertEqual(response.status_code, 200)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(kwargs["params"], {"code": "PCS13", "_count": "10"})

    def test_get_list_propagates_upstream_error_payload(self):
        """Une erreur d'openIMIS est relayée avec son code HTTP et son corps."""
        error_payload = {"detail": "Authentication credentials were not provided."}
        with patch(REQUESTS_PATH, return_value=fake_upstream_response(401, error_payload)):
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition")
            response = getActivityDefinition(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, error_payload)

    def test_get_list_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502."""
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition")
            response = getActivityDefinition(request)

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # GET par identifiant
    # ------------------------------------------------------------------
    def test_get_by_id_forwards_id_and_returns_upstream_data(self):
        """Le GET par identifiant appelle /ActivityDefinition/<id>/ sur openIMIS."""
        expected_payload = {"resourceType": "ActivityDefinition", "id": RESOURCE_ID}
        with patch(
            REQUESTS_PATH, return_value=fake_upstream_response(200, expected_payload)
        ) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition/" + RESOURCE_ID)
            response = getActivityDefinition(request, resource_id=RESOURCE_ID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_payload)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], BASE_URL + RESOURCE_ID + "/")
        self.assertEqual(kwargs["params"], {})

    def test_get_by_unknown_id_propagates_404(self):
        """Un identifiant inconnu : le 404 d'openIMIS est relayé tel quel."""
        error_payload = {
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found"}],
        }
        with patch(REQUESTS_PATH, return_value=fake_upstream_response(404, error_payload)):
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition/unknown")
            response = getActivityDefinition(request, resource_id="unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_payload)

    def test_get_by_id_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502, même pour un GET par identifiant."""
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/ActivityDefinition/" + RESOURCE_ID)
            response = getActivityDefinition(request, resource_id=RESOURCE_ID)

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # Méthodes non supportées
    # ------------------------------------------------------------------
    def test_unsupported_methods_return_405(self):
        """POST, PUT, PATCH et DELETE renvoient 405 sans appeler openIMIS."""
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                with patch(REQUESTS_PATH) as mock_request:
                    request = getattr(self.factory, method)(
                        "/api/api_fhir_r4/ActivityDefinition/" + RESOURCE_ID, {}, format="json"
                    )
                    response = getActivityDefinition(request, resource_id=RESOURCE_ID)

                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 405)
