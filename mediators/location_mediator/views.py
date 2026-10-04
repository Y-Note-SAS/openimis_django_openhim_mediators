"""
openHIM Location mediator: exposes the openIMIS FHIR R4 Location resource (GET).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET"])
def getLocation(request):
	return proxy_fhir_request(request, "Location", trailing_slash=True)


def registerLocationMediator():
	register_fhir_mediator(
		"Location",
		urn="urn:mediator:python_fhir_r4_Location_mediator",
		version="1.0.0",
		name="openIMIS Fhir R4 Location Mediator",
		description="openIMIS Fhir R4 Location Mediator",
		methods=("GET",),
	)
