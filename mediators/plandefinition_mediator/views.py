"""
openHIM PlanDefinition mediator: exposes the openIMIS FHIR R4 PlanDefinition resource
(CSU programmes of the openIMIS "program" module), read-only: GET list/search and GET by id.

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET"])
def getPlanDefinition(request, resource_id=None):
	return proxy_fhir_request(request, "PlanDefinition", resource_id, trailing_slash=True)


def registerPlanDefinitionMediator():
	register_fhir_mediator(
		"PlanDefinition",
		urn="urn:mediator:python_fhir_r4_PlanDefinition_mediator",
		methods=("GET",),
		url_pattern="^/api/api_fhir_r4/PlanDefinition(/[^/]+)?$",
	)
