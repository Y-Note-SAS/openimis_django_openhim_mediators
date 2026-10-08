"""
Settings for openhim ActivityDefinition mediator developed in Django.

The python-based ActivityDefinition mediator implements python-utils
from https://github.com/de-laz/openhim-mediator-utils-py.git.

Read-only mediator: only GET is exposed. In openIMIS, the FHIR ActivityDefinition
resource represents the medical services (openIMIS "services").
  GET /api/api_fhir_r4/ActivityDefinition          -> list / search (query params forwarded)
  GET /api/api_fhir_r4/ActivityDefinition/<id>     -> one ActivityDefinition by its identifier

"""

import base64
import json

import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from openhim_mediator_utils.main import Main
from overview.views import configview


@api_view(['GET'])
def getActivityDefinition(request, resource_id=None):
	result = configview()
	configurations = result.__dict__
	authvars = configurations["data"]["openimis_user"]+":"+configurations["data"]["openimis_passkey"]
	# Standard Base64 Encoding
	encodedBytes = base64.b64encode(authvars.encode("utf-8"))
	encodedStr = str(encodedBytes, "utf-8")
	auth_openimis = "Basic " + encodedStr
	url = configurations["data"]["openimis_url"]+":"+str(configurations["data"]["openimis_port"])+"/api/api_fhir_r4/ActivityDefinition/"

	# GET par identifiant : /ActivityDefinition/<id>/
	if resource_id:
		url = url + resource_id + "/"
	# Transmet les paramètres de recherche FHIR tels quels (ex. ?code=..., ?_count=...)
	querystring = request.query_params.dict()
	headers = {'Authorization': auth_openimis}
	response = requests.request("GET", url, data="", headers=headers, params=querystring)
	try:
		datac = json.loads(response.text)
	except ValueError:
		return Response(
			{"error": "Invalid response received from openIMIS"},
			status=status.HTTP_502_BAD_GATEWAY,
		)
	return Response(datac, status=response.status_code)


def registerActivityDefinitionMediator():
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
	"urn": "urn:mediator:openimis_fhir_r4_activitydefinition_mediator",
	"version": "1.0.0",
	"name": "openIMIS Fhir R4 ActivityDefinition Mediator",
	"description": "openIMIS Fhir R4 ActivityDefinition Mediator (services médicaux)",

	"defaultChannelConfig": [
		{
			"name": "openIMIS Fhir R4 ActivityDefinition Mediator",
			# Liste (/ActivityDefinition) et ressource précise (/ActivityDefinition/<id>)
			"urlPattern": "^/api/api_fhir_r4/ActivityDefinition(/[^/]+)?/?$",
			"routes": [
				{
					# Pas de "path" : openHIM transmet le chemin d'origine (avec l'identifiant)
					"name": "openIMIS Fhir R4 ActivityDefinition Mediator Route",
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
			"path": "/api/api_fhir_r4/ActivityDefinition",
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
