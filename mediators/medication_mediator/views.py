"""
openHIM Medication mediator: exposes the openIMIS FHIR R4 Medication resource
(medicines and consumables, the openIMIS "items"), read-only: GET list/search and GET by id.

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET"])
def getMedication(request, resource_id=None):
	return proxy_fhir_request(request, "Medication", resource_id, trailing_slash=True)


def registerMedicationMediator():
	register_fhir_mediator(
		"Medication",
		urn="urn:mediator:python_fhir_r4_Medication_mediator",
		methods=("GET",),
		url_pattern="^/api/api_fhir_r4/Medication(/[^/]+)?$",
	)
