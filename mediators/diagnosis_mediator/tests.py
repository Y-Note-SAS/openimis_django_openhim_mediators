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

PATH = "/api/api_fhir_r4/CodeSystem/diagnosis"
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


class GetDiagnosisTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        patcher = patch(
            "overview.fhir_proxy.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get(self, upstream=None, code=None, query=None):
        upstream = upstream or fake_upstream_response(200, CODE_SYSTEM)
        with patch(
            "overview.fhir_proxy.requests.request", return_value=upstream
        ) as mock_request:
            url = PATH + ("/" + code if code else "")
            response = getDiagnosis(self.factory.get(url, query or {}), code=code)
        return response, mock_request

    # ------------------------------------------------------------------
    # GET liste
    # ------------------------------------------------------------------
    def test_get_list_returns_all_diagnoses(self):
        """Sans paramètre, la liste complète d'openIMIS est renvoyée telle quelle."""
        response, mock_request = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, CODE_SYSTEM)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], UPSTREAM)
        self.assertEqual(kwargs["params"], {})

    def test_pagination_params_are_not_forwarded(self):
        """_count et _offset sont traités par le médiateur, pas par openIMIS."""
        _, mock_request = self._get(query={"_count": "2", "_offset": "1", "_format": "json"})
        self.assertEqual(mock_request.call_args[1]["params"], {"_format": "json"})

    def test_get_list_with_count_returns_first_page(self):
        """_count limite le nombre de diagnostics ; count reste le total."""
        response, _ = self._get(query={"_count": "2"})
        self.assertEqual([c["code"] for c in response.data["concept"]], ["A00", "A01"])
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["content"], "fragment")

    def test_get_list_with_count_and_offset_returns_requested_page(self):
        """_offset décale le début de la page."""
        response, _ = self._get(query={"_count": "2", "_offset": "2"})
        self.assertEqual([c["code"] for c in response.data["concept"]], ["JB20", "Z00"])

    def test_offset_beyond_end_returns_empty_page(self):
        """Un décalage au-delà de la fin renvoie une page vide, pas une erreur."""
        response, _ = self._get(query={"_count": "2", "_offset": "10"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["concept"], [])

    def test_invalid_pagination_returns_400_without_calling_openimis(self):
        """Une pagination invalide renvoie 400 (OperationOutcome) sans appeler openIMIS."""
        for params in ({"_count": "abc"}, {"_count": "-1"}, {"_offset": "x"}):
            with self.subTest(params=params):
                with patch("overview.fhir_proxy.requests.request") as mock_request:
                    response = getDiagnosis(self.factory.get(PATH, params))
                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["resourceType"], "OperationOutcome")

    def test_get_list_propagates_upstream_error(self):
        """Une erreur d'openIMIS est relayée avec son code HTTP et son corps."""
        error = {"detail": "Authentication credentials were not provided."}
        response, _ = self._get(fake_upstream_response(401, error))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, error)

    def test_get_list_returns_502_when_upstream_body_is_not_json(self):
        """Un corps non JSON reçu d'openIMIS produit un 502."""
        response, _ = self._get(fake_upstream_response(200, text="<html>not json</html>"))
        self.assertEqual(response.status_code, 502)

    # ------------------------------------------------------------------
    # GET par code
    # ------------------------------------------------------------------
    def test_get_by_code_returns_only_matching_diagnosis(self):
        """Le CodeSystem renvoyé ne contient que le diagnostic demandé."""
        response, mock_request = self._get(code="JB20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["concept"], [{"code": "JB20", "display": "Single spontaneous delivery"}]
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["content"], "fragment")
        # openIMIS n'a pas de lecture par code : c'est toujours la liste qui est appelée
        self.assertEqual(mock_request.call_args[0][1], UPSTREAM)

    def test_get_by_code_is_case_insensitive(self):
        """Le code est comparé sans tenir compte de la casse."""
        response, _ = self._get(code="jb20")
        self.assertEqual(response.data["concept"][0]["code"], "JB20")

    def test_get_by_unknown_code_returns_404_operation_outcome(self):
        """Un code inconnu renvoie 404 au format OperationOutcome."""
        response, _ = self._get(code="ZZZ99")
        self.assertEqual(response.status_code, 404)
        issue = response.data["issue"][0]
        self.assertEqual(issue["code"], "not-found")
        self.assertIn("ZZZ99", issue["details"]["text"])

    def test_get_by_code_without_concept_list_returns_404(self):
        """Si openIMIS ne renvoie aucune liste de diagnostics, la recherche donne 404."""
        response, _ = self._get(fake_upstream_response(200, {"resourceType": "CodeSystem"}), code="A00")
        self.assertEqual(response.status_code, 404)

    def test_get_by_code_propagates_upstream_error(self):
        """Une erreur d'openIMIS est relayée telle quelle, même pour un GET par code."""
        response, _ = self._get(fake_upstream_response(500, {"error": "x"}), code="A00")
        self.assertEqual(response.status_code, 500)

    def test_unsupported_methods_return_405(self):
        """POST, PUT, PATCH et DELETE renvoient 405 sans appeler openIMIS."""
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                with patch("overview.fhir_proxy.requests.request") as mock_request:
                    response = getDiagnosis(getattr(self.factory, method)(PATH, {}, format="json"))
                mock_request.assert_not_called()
                self.assertEqual(response.status_code, 405)
