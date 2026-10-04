"""
openHIM Coverage mediator: exposes the openIMIS FHIR R4 Coverage resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getCoverage(request):
	return proxy_fhir_request(request, "Coverage")


def registerCoverageMediator():
	register_fhir_mediator(
		"Coverage",
		urn="urn:mediator:python_fhir_r4_Coverage_mediator",
		version="1.0.1",
		name="Python Fhir R4 Coverage Mediator",
		description="Python Fhir R4 Coverage Mediator",
		methods=("GET", "POST"),
	)
