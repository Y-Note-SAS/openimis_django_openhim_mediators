import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from contract_mediator.views import getContract

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

PATH = "/api/api_fhir_r4/Contract"


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


class getContractTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        patcher = patch(
            "contract_mediator.views.configview",
            return_value=FakeConfigResult(FAKE_CONFIG_DATA),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _call(self, method, upstream, body=None, query=None):
        with patch(
            "contract_mediator.views.requests.request", return_value=upstream
        ) as mock_request:
            if method == "get":
                request = self.factory.get(PATH, query or {})
            else:
                request = self.factory.post(PATH, body or {}, format="json")
            response = getContract(request)
        return response, mock_request

    def test_get_forwards_request_and_returns_upstream_data(self):
        payload = {"resourceType": "Bundle", "entry": []}
        response, mock_request = self._call("get", fake_upstream_response(200, payload))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, payload)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], "http://openimis.local:8080" + PATH)
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Basic "))

    def test_get_forwards_query_params_without_empty_key(self):
        response, mock_request = self._call(
            "get", fake_upstream_response(200, {}), query={"identifier": "123"}
        )
        self.assertEqual(mock_request.call_args[1]["params"], {"identifier": "123"})

    def test_get_without_query_params_sends_no_params(self):
        response, mock_request = self._call("get", fake_upstream_response(200, {}))
        self.assertEqual(mock_request.call_args[1]["params"], {})

    def test_get_propagates_upstream_error_status(self):
        error = {"error": "not found"}
        response, _ = self._call("get", fake_upstream_response(404, error))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error)

    def test_get_returns_502_when_upstream_body_is_not_json(self):
        response, _ = self._call(
            "get", fake_upstream_response(200, text="<html>not json</html>")
        )
        self.assertEqual(response.status_code, 502)

    def test_post_forwards_body_and_propagates_status(self):
        body = {"resourceType": "Contract", "id": "1"}
        payload = {"resourceType": "Contract", "id": "1", "created": True}
        response, mock_request = self._call(
            "post", fake_upstream_response(201, payload), body=body
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, payload)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(json.loads(kwargs["data"]), body)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertNotIn("params", kwargs)

    def test_post_propagates_upstream_error_status(self):
        error = {"error": "invalid"}
        response, _ = self._call("post", fake_upstream_response(400, error))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, error)

    def test_post_returns_502_when_upstream_body_is_not_json(self):
        response, _ = self._call(
            "post", fake_upstream_response(201, text="<html>not json</html>")
        )
        self.assertEqual(response.status_code, 502)

    def test_unsupported_method_returns_405(self):
        with patch("contract_mediator.views.requests.request") as mock_request:
            response = getContract(self.factory.delete(PATH))
        mock_request.assert_not_called()
        self.assertEqual(response.status_code, 405)
