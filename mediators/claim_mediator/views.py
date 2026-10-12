"""
openHIM Claim mediator: exposes the openIMIS FHIR R4 Claim resource
(GET list/search, GET by id, POST, PATCH by id).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST", "PATCH"])
def getClaims(request, resource_id=None):
	# POST crée une demande : uniquement sur la collection, jamais sur /Claim/<id>
	if resource_id and request.method == "POST":
		return Response(
			{"error": "POST is not allowed on a specific Claim"},
			status=status.HTTP_405_METHOD_NOT_ALLOWED,
		)
	# PATCH sans identifiant : 400, géré par le proxy commun
	return proxy_fhir_request(request, "Claim", resource_id, trailing_slash=True)


def registerClaimsMediator():
	register_fhir_mediator(
		"Claim",
		urn="urn:mediator:openimis_fhir_r4_claim_mediator",
		methods=("GET", "POST", "PATCH"),
		url_pattern="^/api/api_fhir_r4/Claim(/[^/]+)?$",
	)
