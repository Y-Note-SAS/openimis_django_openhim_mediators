"""
openHIM Patient mediator: exposes the openIMIS FHIR R4 Patient resource (GET/POST/PATCH).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST", "PATCH"])
def getPatient(request, resource_id=None):
	return proxy_fhir_request(request, "Patient", resource_id, trailing_slash=True)


def registerPatientMediator():
	register_fhir_mediator(
		"Patient",
		urn="urn:mediator:python_fhir_r4_Patient_mediator",
		methods=("GET", "POST", "PATCH"),
		url_pattern="^/api/api_fhir_r4/Patient(/[^/]+)?$",
	)
