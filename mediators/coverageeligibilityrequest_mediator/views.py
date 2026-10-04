"""
openHIM CoverageEligibilityRequest mediator: exposes the openIMIS FHIR R4 CoverageEligibilityRequest resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getCoverageEligibilityRequest(request):
	return proxy_fhir_request(request, "CoverageEligibilityRequest")


def registerCoverageEligibilityRequestMediator():
	register_fhir_mediator(
		"CoverageEligibilityRequest",
		urn="urn:mediator:python_fhir_r4_CoverageEligibilityRequest_mediator",
		methods=("GET", "POST"),
	)
