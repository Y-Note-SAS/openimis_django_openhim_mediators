"""
Shared logic of the openHIM <-> openIMIS FHIR R4 mediators.

Every mediator app (claim, patient, group...) only differs by the FHIR resource
it proxies, the methods it exposes and its openHIM registration metadata, so the
request forwarding and the openHIM registration live here once.
"""

import base64
import json

import requests
from rest_framework import status
from rest_framework.response import Response

from openhim_mediator_utils.main import Main

from overview.views import configview

API_PREFIX = "/api/api_fhir_r4/"
# Single version for all mediators; bump it whenever a registration changes so
# openHIM picks up the new configuration.
MEDIATOR_VERSION = "1.0.3"


def _openimis_auth_header(data):
	credentials = data["openimis_user"] + ":" + data["openimis_passkey"]
	return "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("utf-8")


def _forward(method, url, headers, **kwargs):
	"""Call openIMIS and relay its payload and status code.

	A non-JSON upstream body (HTML error page, proxy error...) is reported as 502
	instead of crashing the view with a 500.
	"""
	response = requests.request(method, url, headers=headers, **kwargs)
	try:
		datac = json.loads(response.text)
	except ValueError:
		return Response(
			{"error": "Invalid response received from openIMIS"},
			status=status.HTTP_502_BAD_GATEWAY,
		)
	return Response(datac, status=response.status_code)


def proxy_fhir_request(request, resource, resource_id=None, trailing_slash=False):
	"""Forward a GET/POST/PATCH on a FHIR ``resource`` to openIMIS.

	GET forwards the incoming query params (FHIR search); with ``resource_id`` it
	reads that single resource (``<resource>/<id>/``). POST/PATCH forward the
	JSON body. PATCH requires ``resource_id`` and returns 400 without it. Methods
	a view does not allow are rejected earlier by ``@api_view`` (405).

	``trailing_slash`` appends "/" to the openIMIS URL (Patient, Group, Location).
	"""
	# configview() returns a DRF Response; its payload is read through __dict__
	# like everywhere else in the project.
	data = configview().__dict__["data"]
	auth = {"Authorization": _openimis_auth_header(data)}
	url = "%s:%s%s%s%s" % (
		data["openimis_url"], data["openimis_port"], API_PREFIX, resource,
		"/" if trailing_slash else "",
	)

	if request.method == 'GET':
		if resource_id:
			url = url.rstrip("/") + "/" + resource_id + "/"
		return _forward("GET", url, auth, data="", params=request.query_params.dict())

	headers = dict(auth, **{"Content-Type": "application/json"})
	body = json.dumps(request.data)
	if request.method == 'POST':
		return _forward("POST", url, headers, data=body)
	if request.method == 'PATCH':
		if not resource_id:
			return Response(
				{"error": "A %s id is required in the URL to PATCH (e.g. %s%s/<id>)"
					% (resource, API_PREFIX, resource)},
				status=status.HTTP_400_BAD_REQUEST,
			)
		return _forward("PATCH", url.rstrip("/") + "/" + resource_id + "/", headers, data=body)


def register_fhir_mediator(resource, urn, methods=("GET", "POST"), url_pattern=None,
		display_name=None):
	"""Register the mediator of ``resource`` with openHIM and start its heartbeat.

	Name and description follow "openIMIS Fhir R4 <display_name> Mediator"
	(``display_name`` defaults to ``resource``, e.g. "Diagnosis" for the
	"CodeSystem/diagnosis" resource) and the version is MEDIATOR_VERSION for
	every mediator.

	With a custom ``url_pattern`` (typically one accepting an id, such as
	``^/api/api_fhir_r4/Patient(/[^/]+)?$``), the default route has no "path":
	openHIM then forwards the original path, id included, to the mediator.
	"""
	name = "openIMIS Fhir R4 %s Mediator" % (display_name or resource)
	data = configview().__dict__["data"]
	path = API_PREFIX + resource

	options = {
		'verify_cert': False,
		'apiURL': 'https://' + data["openhim_url"] + ':' + str(data["openhim_port"]),
		'username': data["openhim_user"],
		'password': data["openhim_passkey"],
		'force_config': False,
		'interval': 10,
	}

	route = {
		"name": name + " Route",
		"host": data["mediator_url"],
		"port": data["mediator_port"],
		"primary": True,
		"type": "http",
	}
	if url_pattern is None:
		route["path"] = path

	conf = {
		"urn": urn,
		"version": MEDIATOR_VERSION,
		"name": name,
		"description": name,
		"defaultChannelConfig": [
			{
				"name": name,
				"urlPattern": url_pattern or "^" + path + "$",
				"routes": [route],
				"allow": ["admin"],
				"methods": list(methods),
				"type": "http",
			}
		],
		"endpoints": [
			{
				"name": "Bootstrap Scaffold Mediator Endpoint",
				"host": data["mediator_url"],
				"path": path,
				"port": data["mediator_port"],
				"primary": True,
				"type": "http",
			}
		],
	}

	openhim_mediator_utils = Main(options=options, conf=conf)
	openhim_mediator_utils.register_mediator()
	# Monitor the health status of the client on the console
	openhim_mediator_utils.activate_heartbeat()
