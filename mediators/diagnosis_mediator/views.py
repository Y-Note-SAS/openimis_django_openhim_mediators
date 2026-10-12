"""
Settings for openhim Diagnosis mediator developed in Django.

The python-based Diagnosis mediator implements python-utils
from https://github.com/de-laz/openhim-mediator-utils-py.git.

Read-only mediator: only GET is exposed. openIMIS publishes its diagnoses
as a single FHIR CodeSystem resource (/api/api_fhir_r4/CodeSystem/diagnosis/)
whose "concept" list holds every diagnosis (code + display).

openIMIS has no "get by code" endpoint for this CodeSystem, so the mediator
provides it: it fetches the CodeSystem and keeps only the requested concept.

"""

import base64
import json

import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from openhim_mediator_utils.main import Main
from overview.views import configview

# Paramètres de pagination traités par le médiateur (non transmis à openIMIS)
PAGINATION_PARAMS = ("_count", "_offset")


def _operation_outcome(code, text, http_status):
	"""Construit une réponse d'erreur au format FHIR OperationOutcome."""
	return Response(
		{
			"resourceType": "OperationOutcome",
			"issue": [
				{
					"severity": "error",
					"code": code,
					"details": {"text": text},
				}
			],
		},
		status=http_status,
	)


def _read_non_negative_int(params, name):
	"""Lit un paramètre entier positif ou nul. Renvoie None s'il est absent.

	Lève ValueError si la valeur n'est pas un entier positif ou nul.
	"""
	raw = params.get(name)
	if raw is None:
		return None
	value = int(raw)
	if value < 0:
		raise ValueError(name)
	return value


def _concepts(code_system):
	"""Renvoie la liste des diagnostics d'un CodeSystem (liste vide si absente)."""
	concepts = code_system.get("concept") if isinstance(code_system, dict) else None
	return concepts if isinstance(concepts, list) else []


@api_view(['GET'])
def getDiagnosis(request, code=None):
	result = configview()
	configurations = result.__dict__
	authvars = configurations["data"]["openimis_user"]+":"+configurations["data"]["openimis_passkey"]
	# Standard Base64 Encoding
	encodedBytes = base64.b64encode(authvars.encode("utf-8"))
	encodedStr = str(encodedBytes, "utf-8")
	auth_openimis = "Basic " + encodedStr
	url = configurations["data"]["openimis_url"]+":"+str(configurations["data"]["openimis_port"])+"/api/api_fhir_r4/CodeSystem/diagnosis/"

	params = request.query_params.dict()

	# Pagination : validée avant tout appel à openIMIS
	try:
		count = _read_non_negative_int(params, "_count")
		offset = _read_non_negative_int(params, "_offset") or 0
	except ValueError:
		return _operation_outcome(
			"invalid",
			"_count and _offset must be non-negative integers",
			status.HTTP_400_BAD_REQUEST,
		)

	# Les autres paramètres sont transmis tels quels à openIMIS
	querystring = {k: v for k, v in params.items() if k not in PAGINATION_PARAMS}
	headers = {'Authorization': auth_openimis}
	response = requests.request("GET", url, data="", headers=headers, params=querystring)
	try:
		datac = json.loads(response.text)
	except ValueError:
		return Response(
			{"error": "Invalid response received from openIMIS"},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	# Erreur d'openIMIS (401, 403, 500...) : relayée telle quelle
	if response.status_code != 200:
		return Response(datac, status=response.status_code)

	concepts = _concepts(datac)

	# GET par code : /CodeSystem/diagnosis/<code>
	if code is not None:
		wanted = code.strip().upper()
		matches = [c for c in concepts if str(c.get("code", "")).upper() == wanted]
		if not matches:
			return _operation_outcome(
				"not-found",
				"Diagnosis with code '%s' was not found" % code,
				status.HTTP_404_NOT_FOUND,
			)
		datac["concept"] = matches[:1]
		datac["count"] = 1
		datac["content"] = "fragment"
		return Response(datac, status=status.HTTP_200_OK)

	# GET liste : la liste complète par défaut, une page si _count ou _offset est fourni
	if count is not None or offset:
		end = None if count is None else offset + count
		datac["concept"] = concepts[offset:end]
		# "count" reste le nombre total de diagnostics, pour permettre de paginer
		datac["count"] = len(concepts)
		datac["content"] = "fragment"
	return Response(datac, status=status.HTTP_200_OK)


def registerDiagnosisMediator():
	result = configview()
	configurations = result.__dict__

	API_URL = 'https://'+configurations["data"]["openhim_url"]+':'+str(configurations["data"]["openhim_port"])
	USERNAME = configurations["data"]["openhim_user"]
	PASSWORD = configurations["data"]["openhim_passkey"]

	options = {
	'verify_cert': False,
	'apiURL': API_URL,
	'username': USERNAME,
	'password': PASSWORD,
	'force_config': False,
	'interval': 10,
	}

	conf = {
	"urn": "urn:mediator:openimis_fhir_r4_diagnosis_mediator",
	"version": "1.0.0",
	"name": "openIMIS Fhir R4 Diagnosis Mediator",
	"description": "openIMIS Fhir R4 Diagnosis Mediator",

	"defaultChannelConfig": [
		{
			"name": "openIMIS Fhir R4 Diagnosis Mediator",
			# Liste (/CodeSystem/diagnosis) et diagnostic précis (/CodeSystem/diagnosis/<code>)
			"urlPattern": "^/api/api_fhir_r4/CodeSystem/diagnosis(/[^/]+)?/?$",
			"routes": [
				{
					# Pas de "path" : openHIM transmet le chemin d'origine (avec le code)
					"name": "openIMIS Fhir R4 Diagnosis Mediator Route",
					"host": configurations["data"]["mediator_url"],
					"port": configurations["data"]["mediator_port"],
					"primary": True,
					"type": "http"
				}
			],
			"allow": ["admin"],
			"methods": ["GET"],
			"type": "http"
		}
	],

	"endpoints": [
		{
			"name": "Bootstrap Scaffold Mediator Endpoint",
			"host": configurations["data"]["mediator_url"],
			"path": "/api/api_fhir_r4/CodeSystem/diagnosis",
			"port": configurations["data"]["mediator_port"],
			"primary": True,
			"type": "http"
		}
	]
	}

	openhim_mediator_utils = Main(
		options=options,
		conf=conf
		)

	openhim_mediator_utils.register_mediator()
	checkHeartbeat(openhim_mediator_utils)


# Monitoring the health status of the client on the console
def checkHeartbeat(openhim_mediator_utils):
	openhim_mediator_utils.activate_heartbeat()
