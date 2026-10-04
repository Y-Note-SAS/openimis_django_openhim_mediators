"""
openHIM Organisation mediator: exposes the openIMIS FHIR R4 Organisation resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getOrganisation(request):
	return proxy_fhir_request(request, "Organisation")


def registerOrganisationMediator():
	register_fhir_mediator(
		"Organisation",
		urn="urn:mediator:python_fhir_r4_Organisation_mediator",
		version="1.0.1",
		name="Python Fhir R4 Organisation Mediator",
		description="Python Fhir R4 Organisation Mediator",
		methods=("GET", "POST"),
	)
