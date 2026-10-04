"""
openHIM Group mediator: exposes the openIMIS FHIR R4 Group resource (GET/POST/PATCH).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST", "PATCH"])
def getGroup(request, resource_id=None):
	return proxy_fhir_request(request, "Group", resource_id, trailing_slash=True)


def registerGroupMediator():
	register_fhir_mediator(
		"Group",
		urn="urn:mediator:openimis_fhir_r4_Group_mediator",
		methods=("GET", "POST", "PATCH"),
		url_pattern="^/api/api_fhir_r4/Group(/[^/]+)?$",
	)
