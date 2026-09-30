"""
Settings for openhim Patient mediator developed in Django.

The python-based Patient mediator implements python-utils 
from https://github.com/de-laz/openhim-mediator-utils-py.git.

For more information on this file, contact the Python developers
Stephen Mburu:ahoazure@gmail.com & Peter Kaniu:peterkaniu254@gmail.com

"""

from django.shortcuts import render

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import http.client

import json


import urllib3
import requests
from datetime import datetime
from openhim_mediator_utils.main import Main
from time import sleep

from overview.models import configs
from overview.views import configview
import http.client
import base64


@api_view(['GET', 'POST', 'PATCH'])
def getPatient(request, resource_id=None):
	result = configview()
	configurations = result.__dict__
	authvars = configurations["data"]["openimis_user"]+":"+configurations["data"]["openimis_passkey"]#username:password-openhimclient:openhimclientPasskey
	# Standard Base64 Encoding
	encodedBytes = base64.b64encode(authvars.encode("utf-8"))
	encodedStr = str(encodedBytes, "utf-8")
	auth_openimis = "Basic " + encodedStr
	url = configurations["data"]["openimis_url"]+":"+str(configurations["data"]["openimis_port"])+"/api/api_fhir_r4/Patient/"
	# Query the upstream server via openHIM mediator port 8000
	# Caution: To secure the endpoint with SSL certificate,FQDN is required 
	if request.method == 'GET':
		# Forward incoming FHIR search params as-is (e.g. ?identifier=..., ?name=...)
		# so searching for a specific patient works, not just listing all patients.
		querystring = request.query_params.dict()
		payload = ""
		headers = {'Authorization': auth_openimis}
		response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
		try:
			datac = json.loads(response.text)
		except ValueError:
			return Response(
				{"error": "Invalid response received from openIMIS"},
				status=status.HTTP_502_BAD_GATEWAY,
			)
		return Response(datac, status=response.status_code)
	elif request.method == 'POST':
		data = json.dumps(request.data)
		payload = data
		headers = {
			'Content-Type': "application/json",
			'Authorization': auth_openimis
			}
		response = requests.request("POST", url, data=payload, headers=headers)
		try:
			datac = json.loads(response.text)
		except ValueError:
			return Response(
				{"error": "Invalid response received from openIMIS"},
				status=status.HTTP_502_BAD_GATEWAY,
			)
		return Response(datac, status=response.status_code)
	elif request.method == 'PATCH':
		if not resource_id:
			return Response(
				{"error": "A Patient id is required in the URL to PATCH (e.g. /api/api_fhir_r4/Patient/<id>)"},
				status=status.HTTP_400_BAD_REQUEST,
			)
		data = json.dumps(request.data)
		payload = data
		headers = {
			'Content-Type': "application/json",
			'Authorization': auth_openimis
			}
		response = requests.request("PATCH", url + resource_id + "/", data=payload, headers=headers)
		try:
			datac = json.loads(response.text)
		except ValueError:
			return Response(
				{"error": "Invalid response received from openIMIS"},
				status=status.HTTP_502_BAD_GATEWAY,
			)
		return Response(datac, status=response.status_code)


def registerPatientMediator():
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
	"urn": "urn:mediator:python_fhir_r4_Patient_mediator",
	"version": "1.0.2",
	"name": "openIMIS Fhir R4 Patient Mediator",
	"description": "openIMIS Fhir R4 Patient Mediator",

	"defaultChannelConfig": [
		{
			"name": "openIMIS Fhir R4 Patient Mediator",
			"urlPattern": "^/api/api_fhir_r4/Patient(/[^/]+)?$",
			"routes": [
				{
					"name": "openIMIS Fhir R4 Patient Mediator Route",
					"host": configurations["data"]["mediator_url"],
					"path": "/api/api_fhir_r4/Patient",
					"port": configurations["data"]["mediator_port"],
					"primary": True,
					"type": "http"
				}
			],
			"allow": ["admin"],
			"methods": ["GET", "POST", "PATCH"],
			"type": "http"
		}
	],

	"endpoints": [
		{
			"name": "Bootstrap Scaffold Mediator Endpoint",
			"host": configurations["data"]["mediator_url"],
			"path": "/api/api_fhir_r4/Patient",
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



# Morning the health status of the client on the console
def checkHeartbeat(openhim_mediator_utils):
	openhim_mediator_utils.activate_heartbeat()
