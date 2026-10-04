"""
openHIM Contract mediator: exposes the openIMIS FHIR R4 Contract resource (GET/POST).

The forwarding and registration logic is shared in overview.fhir_proxy.
"""

from rest_framework.decorators import api_view

from overview.fhir_proxy import proxy_fhir_request, register_fhir_mediator


@api_view(["GET", "POST"])
def getContract(request):
	return proxy_fhir_request(request, "Contract")


def registerContractMediator():
	register_fhir_mediator(
		"Contract",
		urn="urn:mediator:python_fhir_r4_Contract_mediator",
		version="1.0.1",
		name="Python Fhir R4 Contract Mediator",
		description="Python Fhir R4 Contract Mediator",
		methods=("GET", "POST"),
	)
