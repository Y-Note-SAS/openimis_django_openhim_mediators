"""
openHIM Organisation mediator: exposes the openIMIS FHIR R4 Organisation resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getOrganisation(request):
	# openIMIS expose la ressource sous l'orthographe FHIR « Organization »,
	# avec une barre oblique finale (sans elle : redirection 301).
	return proxy_fhir_request(request, "Organization", trailing_slash=True)


def registerOrganisationMediator():
	register_fhir_mediator(
		"Organisation",
		urn="urn:mediator:python_fhir_r4_Organisation_mediator",
		methods=("GET", "POST"),
	)
