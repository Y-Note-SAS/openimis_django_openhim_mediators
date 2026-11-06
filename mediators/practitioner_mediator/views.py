"""
openHIM Practitioner mediator: exposes the openIMIS FHIR R4 Practitioner resource
(GET list/search, GET by id).

In openIMIS, a Practitioner is a claim administrator or an enrolment officer.
EMRs need it to fill the "enterer" of a Claim.

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET"])
def getPractitioner(request, resource_id=None):
	return proxy_fhir_request(request, "Practitioner", resource_id, trailing_slash=True)


def registerPractitionerMediator():
	register_fhir_mediator(
		"Practitioner",
		urn="urn:mediator:python_fhir_r4_Practitioner_mediator",
		methods=("GET",),
		url_pattern="^/api/api_fhir_r4/Practitioner(/[^/]+)?$",
	)
