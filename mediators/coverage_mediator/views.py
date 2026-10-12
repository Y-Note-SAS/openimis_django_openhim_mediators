"""
openHIM Coverage mediator: exposes the openIMIS FHIR R4 Coverage resource
(GET list/search, GET by id, POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getCoverage(request, resource_id=None):
	# POST crée une ressource : uniquement sur la collection, jamais sur /Coverage/<id>
	if resource_id and request.method == "POST":
		return Response(
			{"error": "POST is not allowed on a specific Coverage"},
			status=status.HTTP_405_METHOD_NOT_ALLOWED,
		)
	return proxy_fhir_request(request, "Coverage", resource_id)


def registerCoverageMediator():
	register_fhir_mediator(
		"Coverage",
		urn="urn:mediator:python_fhir_r4_Coverage_mediator",
		methods=("GET", "POST",),
		url_pattern="^/api/api_fhir_r4/Coverage(/[^/]+)?$",
	)
