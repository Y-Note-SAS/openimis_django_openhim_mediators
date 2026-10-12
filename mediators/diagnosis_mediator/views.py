"""
openHIM Diagnosis mediator: exposes the openIMIS diagnoses (FHIR R4 CodeSystem
"diagnosis"), read-only.

openIMIS publishes every diagnosis in a single CodeSystem resource
(/api/api_fhir_r4/CodeSystem/diagnosis/) whose "concept" list holds the code
and display of each diagnosis. openIMIS has no "get by code" endpoint, so the
mediator provides it, plus an optional pagination (_count, _offset):
  GET /api/api_fhir_r4/CodeSystem/diagnosis            -> full list
  GET /api/api_fhir_r4/CodeSystem/diagnosis?_count=50  -> one page
  GET /api/api_fhir_r4/CodeSystem/diagnosis/<code>     -> one diagnosis, or 404

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator

RESOURCE = "CodeSystem/diagnosis"
# Paramètres de pagination traités par le médiateur (non transmis à openIMIS)
PAGINATION_PARAMS = ("_count", "_offset")


def _operation_outcome(code, text, http_status):
	"""Construit une réponse d'erreur au format FHIR OperationOutcome."""
	return Response(
		{
			"resourceType": "OperationOutcome",
			"issue": [{"severity": "error", "code": code, "details": {"text": text}}],
		},
		status=http_status,
	)


def _read_non_negative_int(params, name):
	"""Lit un paramètre entier positif ou nul ; None s'il est absent.

	Lève ValueError si la valeur n'est pas un entier positif ou nul.
	"""
	raw = params.get(name)
	if raw is None:
		return None
	value = int(raw)
	if value < 0:
		raise ValueError(name)
	return value


class _UpstreamRequest:
	"""La requête reçue, sans les paramètres de pagination propres au médiateur.

	proxy_fhir_request ne lit que method, query_params et data.
	"""

	def __init__(self, request):
		self.method = request.method
		self.data = request.data
		self.query_params = request.query_params.copy()
		for name in PAGINATION_PARAMS:
			self.query_params.pop(name, None)


def _concepts(code_system):
	"""Liste des diagnostics d'un CodeSystem (liste vide si absente)."""
	concepts = code_system.get("concept") if isinstance(code_system, dict) else None
	return concepts if isinstance(concepts, list) else []


@api_view(["GET"])
def getDiagnosis(request, code=None):
	# Pagination validée avant tout appel à openIMIS
	try:
		count = _read_non_negative_int(request.query_params, "_count")
		offset = _read_non_negative_int(request.query_params, "_offset") or 0
	except ValueError:
		return _operation_outcome(
			"invalid", "_count and _offset must be non-negative integers",
			status.HTTP_400_BAD_REQUEST,
		)

	# openIMIS n'a pas de lecture par code : on lit toujours la liste complète
	response = proxy_fhir_request(_UpstreamRequest(request), RESOURCE, trailing_slash=True)
	# Erreur d'openIMIS (401, 500...) ou réponse non JSON (502) : relayée telle quelle
	if response.status_code != 200:
		return response

	data = response.data
	concepts = _concepts(data)

	# GET par code : /CodeSystem/diagnosis/<code>
	if code is not None:
		wanted = code.strip().upper()
		matches = [c for c in concepts if str(c.get("code", "")).upper() == wanted]
		if not matches:
			return _operation_outcome(
				"not-found", "Diagnosis with code '%s' was not found" % code,
				status.HTTP_404_NOT_FOUND,
			)
		data["concept"] = matches[:1]
		data["count"] = 1
		data["content"] = "fragment"
		return Response(data, status=status.HTTP_200_OK)

	# GET liste : complète par défaut, une page si _count ou _offset est fourni
	if count is not None or offset:
		end = None if count is None else offset + count
		data["concept"] = concepts[offset:end]
		# "count" reste le nombre total de diagnostics, pour permettre de paginer
		data["count"] = len(concepts)
		data["content"] = "fragment"
	return Response(data, status=status.HTTP_200_OK)


def registerDiagnosisMediator():
	register_fhir_mediator(
		RESOURCE,
		urn="urn:mediator:python_fhir_r4_Diagnosis_mediator",
		methods=("GET",),
		url_pattern="^/api/api_fhir_r4/CodeSystem/diagnosis(/[^/]+)?$",
		display_name="Diagnosis",
	)
