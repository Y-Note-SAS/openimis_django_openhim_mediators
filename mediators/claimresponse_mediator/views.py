"""
Settings for openhim ClaimResponse mediator developed in Django.

The python-based ClaimResponse mediator implements python-utils 
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


def _upstream_response(response):
	"""Relaie la réponse d'openIMIS avec son code HTTP ; 502 si le corps n'est pas du JSON."""
	try:
		datac = json.loads(response.text)
	except ValueError:
		return Response(
			{"error": "Invalid response received from openIMIS"},
			status=status.HTTP_502_BAD_GATEWAY,
		)
	return Response(datac, status=response.status_code)


@api_view(['GET', 'POST'])
def getClaimResponse(request, resource_id=None):
	result = configview()
	configurations = result.__dict__
	authvars = configurations["data"]["openimis_user"]+":"+configurations["data"]["openimis_passkey"]
	encodedBytes = base64.b64encode(authvars.encode("utf-8"))
	encodedStr = str(encodedBytes, "utf-8")
	auth_openimis = "Basic " + encodedStr
	# Barre oblique finale : openIMIS attend /ClaimResponse/ et /ClaimResponse/<id>/
	url = configurations["data"]["openimis_url"]+":"+str(configurations["data"]["openimis_port"])+"/api/api_fhir_r4/ClaimResponse/"

	if request.method == 'GET':
		# GET par identifiant : /ClaimResponse/<id>/
		if resource_id:
			url = url + resource_id + "/"
		# Transmet les paramètres de recherche FHIR (ex. ?request=Claim/<id>)
		querystring = request.query_params.dict()
		headers = {'Authorization': auth_openimis}
		response = requests.request("GET", url, data="", headers=headers, params=querystring)
		return _upstream_response(response)

	elif request.method == 'POST':
		# POST uniquement sur la collection, interdit sur une URL avec identifiant
		if resource_id:
			return Response(
				{"error": "POST is not allowed on a specific ClaimResponse"},
				status=status.HTTP_405_METHOD_NOT_ALLOWED,
			)
		payload = json.dumps(request.data)
		headers = {
			'Content-Type': "application/json",
			'Authorization': auth_openimis
			}
		response = requests.request("POST", url, data=payload, headers=headers)
		return _upstream_response(response)


def registerClaimResponseMediator():
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
	"urn": "urn:mediator:python_fhir_r4_ClaimResponse_mediator",
	"version": "1.0.2",
	"name": "Python Fhir R4 ClaimResponse Mediator",
	"description": "Python Fhir R4 ClaimResponse Mediator",

	"defaultChannelConfig": [
		{
			"name": "Python Fhir R4 ClaimResponse Mediator",
			"urlPattern": "^/api/api_fhir_r4/ClaimResponse(/[^/]+)?/?$",
			"routes": [
				{
					"name": "Python Fhir R4 ClaimResponse Mediator Route",
					"host": configurations["data"]["mediator_url"],
					"port": configurations["data"]["mediator_port"],
					"primary": True,
					"type": "http"
				}
			],
			"allow": ["admin"],
			"methods": ["GET", "POST"],
			"type": "http"
		}
	],

	"endpoints": [
		{
			"name": "Bootstrap Scaffold Mediator Endpoint",
			"host": configurations["data"]["mediator_url"],
			"path": "/api/api_fhir_r4/ClaimResponse",
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
