"""
openHIM Claim mediator: exposes the openIMIS FHIR R4 Claim resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getClaims(request):
	return proxy_fhir_request(request, "Claim")


def registerClaimsMediator():
	register_fhir_mediator(
		"Claim",
		urn="urn:mediator:openimis_fhir_r4_claim_mediator",
		methods=("GET", "POST"),
	)
