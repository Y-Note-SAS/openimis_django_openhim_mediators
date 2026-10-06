import copy
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from diagnosis_mediator.views import getDiagnosis

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

BASE_URL = "http://openimis.local:8080/api/api_fhir_r4/CodeSystem/diagnosis/"
REQUESTS_PATH = "diagnosis_mediator.views.requests.request"

CODE_SYSTEM = {
    "resourceType": "CodeSystem",
    "id": "diagnosis",
    "status": "active",
    "content": "complete",
    "count": 4,
    "concept": [
        {"code": "A00", "display": "Cholera"},
        {"code": "A01", "display": "Typhoid and paratyphoid fevers"},
        {"code": "JB20", "display": "Single spontaneous delivery"},
        {"code": "Z00", "display": "General examination"},
    ],
}


class FakeConfigResult:
    """Imite la réponse DRF renvoyée par overview.views.configview.

    getDiagnosis la lit via result.__dict__["data"] : seul l'attribut "data"
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


class GetDiagnosisTests(TestCase):
    def setUp(self):
        """Prépare la fabrique de requêtes et remplace la configuration par des valeurs factices."""
        self.factory = APIRequestFactory()
        self.config_patcher = patch(
            "diagnosis_mediator.views.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        self.mock_configview = self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    def _upstream(self):
        """Renvoie une copie du CodeSystem d'exemple, pour isoler chaque test."""
        return fake_upstream_response(200, copy.deepcopy(CODE_SYSTEM))

    # ------------------------------------------------------------------
    # GET liste
    # ------------------------------------------------------------------
    def test_get_list_forwards_request_and_returns_all_diagnoses(self):
        """Sans paramètre, la liste complète d'openIMIS est renvoyée telle quelle."""
        with patch(REQUESTS_PATH, return_value=self._upstream()) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis")
            response = getDiagnosis(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, CODE_SYSTEM)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], BASE_URL)
        self.assertEqual(kwargs["params"], {})
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_list_forwards_other_query_params(self):
        """Les paramètres autres que la pagination sont transmis à openIMIS."""
        with patch(REQUESTS_PATH, return_value=self._upstream()) as mock_request:
            request = self.factory.get(
                "/api/api_fhir_r4/CodeSystem/diagnosis", {"_format": "json", "_count": "2"}
            )
            getDiagnosis(request)

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"_format": "json"})

    def test_get_list_with_count_returns_first_page(self):
        """``_count`` limite le nombre de diagnostics ; ``count`` reste le total."""
        with patch(REQUESTS_PATH, return_value=self._upstream()):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis", {"_count": "2"})
            response = getDiagnosis(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["code"] for c in response.data["concept"]], ["A00", "A01"])
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["content"], "fragment")

    def test_get_list_with_count_and_offset_returns_requested_page(self):
        """``_offset`` décale le début de la page."""
        with patch(REQUESTS_PATH, return_value=self._upstream()):
            request = self.factory.get(
                "/api/api_fhir_r4/CodeSystem/diagnosis", {"_count": "2", "_offset": "2"}
            )
            response = getDiagnosis(request)

        self.assertEqual([c["code"] for c in response.data["concept"]], ["JB20", "Z00"])
        self.assertEqual(response.data["count"], 4)

    def test_get_list_with_offset_beyond_end_returns_empty_page(self):
        """Un décalage au-delà de la fin renvoie une page vide, pas une erreur."""
        with patch(REQUESTS_PATH, return_value=self._upstream()):
            request = self.factory.get(
                "/api/api_fhir_r4/CodeSystem/diagnosis", {"_count": "2", "_offset": "10"}
            )
            response = getDiagnosis(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["concept"], [])
        self.assertEqual(response.data["count"], 4)

    def test_get_list_with_invalid_pagination_returns_400_without_calling_openimis(self):
        """Une pagination invalide renvoie 400 (OperationOutcome) sans appeler openIMIS."""
        for params in ({"_count": "abc"}, {"_count": "-1"}, {"_offset": "x"}, {"_offset": "-5"}):
            with self.subTest(params=params):
                with patch(REQUESTS_PATH) as mock_request:
                    request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis", params)
                    response = getDiagnosis(request)

                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["resourceType"], "OperationOutcome")

    def test_get_list_propagates_upstream_error_payload(self):
        """Une erreur d'openIMIS est relayée avec son code HTTP et son corps."""
        error_payload = {"detail": "Authentication credentials were not provided."}
        with patch(REQUESTS_PATH, return_value=fake_upstream_response(401, error_payload)):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis")
            response = getDiagnosis(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, error_payload)

    def test_get_list_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502."""
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis")
            response = getDiagnosis(request)

        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # GET par code
    # ------------------------------------------------------------------
    def test_get_by_code_returns_only_matching_diagnosis(self):
        """Le CodeSystem renvoyé ne contient que le diagnostic demandé."""
        with patch(REQUESTS_PATH, return_value=self._upstream()) as mock_request:
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/JB20")
            response = getDiagnosis(request, code="JB20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["resourceType"], "CodeSystem")
        self.assertEqual(
            response.data["concept"],
            [{"code": "JB20", "display": "Single spontaneous delivery"}],
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["content"], "fragment")

        # openIMIS n'a pas de "get by code" : c'est toujours la liste qui est appelée
        args, _ = mock_request.call_args
        self.assertEqual(args[1], BASE_URL)

    def test_get_by_code_is_case_insensitive(self):
        """Le code est comparé sans tenir compte de la casse."""
        with patch(REQUESTS_PATH, return_value=self._upstream()):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/jb20")
            response = getDiagnosis(request, code="jb20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["concept"][0]["code"], "JB20")

    def test_get_by_unknown_code_returns_404_operation_outcome(self):
        """Un code inconnu renvoie 404 au format OperationOutcome."""
        with patch(REQUESTS_PATH, return_value=self._upstream()):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/ZZZ99")
            response = getDiagnosis(request, code="ZZZ99")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["resourceType"], "OperationOutcome")
        issue = response.data["issue"][0]
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["code"], "not-found")
        self.assertIn("ZZZ99", issue["details"]["text"])

    def test_get_by_code_returns_404_when_upstream_has_no_concept_list(self):
        """Si openIMIS ne renvoie aucune liste de diagnostics, la recherche donne 404."""
        with patch(
            REQUESTS_PATH,
            return_value=fake_upstream_response(200, {"resourceType": "CodeSystem"}),
        ):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/A00")
            response = getDiagnosis(request, code="A00")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["resourceType"], "OperationOutcome")

    def test_get_by_code_propagates_upstream_error_payload(self):
        """Une erreur d'openIMIS est relayée telle quelle, même pour un GET par code."""
        error_payload = {"error": "server error"}
        with patch(REQUESTS_PATH, return_value=fake_upstream_response(500, error_payload)):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/A00")
            response = getDiagnosis(request, code="A00")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, error_payload)

    def test_get_by_code_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502, même pour un GET par code."""
        with patch(REQUESTS_PATH, return_value=broken_upstream_response(200)):
            request = self.factory.get("/api/api_fhir_r4/CodeSystem/diagnosis/A00")
            response = getDiagnosis(request, code="A00")

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
                        "/api/api_fhir_r4/CodeSystem/diagnosis", {}, format="json"
                    )
                    response = getDiagnosis(request)

                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 405)
