"""
openHIM ClaimResponse mediator: exposes the openIMIS FHIR R4 ClaimResponse resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getClaimResponse(request):
	return proxy_fhir_request(request, "ClaimResponse")


def registerClaimResponseMediator():
	register_fhir_mediator(
		"ClaimResponse",
		urn="urn:mediator:python_fhir_r4_ClaimResponse_mediator",
		methods=("GET", "POST"),
	)
