"""
openHIM ActivityDefinition mediator: exposes the openIMIS FHIR R4 ActivityDefinition resource
(medical services, the openIMIS "services"), read-only: GET list/search and GET by id.

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET"])
def getActivityDefinition(request, resource_id=None):
	return proxy_fhir_request(request, "ActivityDefinition", resource_id, trailing_slash=True)


def registerActivityDefinitionMediator():
	register_fhir_mediator(
		"ActivityDefinition",
		urn="urn:mediator:python_fhir_r4_ActivityDefinition_mediator",
		methods=("GET",),
		url_pattern="^/api/api_fhir_r4/ActivityDefinition(/[^/]+)?$",
	)
