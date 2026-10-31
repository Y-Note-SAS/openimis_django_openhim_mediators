"""
FHIR R4 CapabilityStatement of the mediators: GET /api/api_fhir_r4/metadata.

The statement describes what the mediators expose (not everything openIMIS
supports) and is built locally, so it answers even when openIMIS is down or not
configured. RESOURCES is the single list of served resources; a test checks it
against the URLconf and the methods allowed by each view, so the two cannot
drift apart silently.
"""

from datetime import datetime, timezone

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from overview.fhir_proxy import API_PREFIX, MEDIATOR_VERSION, register_fhir_mediator

FHIR_VERSION = "4.0.1"

# (resource type as served in the URL, FHIR interactions, documentation)
# Resource types are the FHIR ones; LEGACY_ALIASES lists the other spellings that
# are still served but not advertised.
RESOURCES = (
	("ActivityDefinition", ("read", "search-type"), None),
	("Claim", ("search-type", "create"), None),
	("ClaimResponse", ("read", "search-type", "create"), None),
	("CodeSystem", ("read",),
		"Only the 'diagnosis' CodeSystem (diagnoses), read-only: "
		"CodeSystem/diagnosis, optional _count/_offset, and CodeSystem/diagnosis/<code>."),
	("Contract", ("search-type", "create"), None),
	("Coverage", ("search-type", "create"), None),
	("CoverageEligibilityRequest", ("search-type", "create"), None),
	("Group", ("read", "search-type", "create", "patch"), None),
	("Location", ("search-type",), None),
	("Medication", ("read", "search-type"), None),
	("Organization", ("search-type", "create"), None),
	("Patient", ("read", "search-type", "create", "patch"), None),
)

# Served URL spelling -> FHIR type advertised in the statement
LEGACY_ALIASES = {"Organisation": "Organization"}


def build_capability_statement(base_url):
	"""The CapabilityStatement as a dict; ``base_url`` is the FHIR endpoint root."""
	resources = []
	for resource_type, interactions, documentation in RESOURCES:
		entry = {
			"type": resource_type,
			"interaction": [{"code": code} for code in interactions],
		}
		if documentation:
			entry["documentation"] = documentation
		resources.append(entry)

	return {
		"resourceType": "CapabilityStatement",
		"status": "active",
		"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
		"kind": "instance",
		"software": {"name": "openIMIS Fhir R4 mediators", "version": MEDIATOR_VERSION},
		"implementation": {
			"description": "openHIM mediators exposing openIMIS FHIR R4 resources",
			"url": base_url,
		},
		"fhirVersion": FHIR_VERSION,
		"format": ["json"],
		"rest": [{"mode": "server", "resource": resources}],
	}


@api_view(["GET"])
def getCapabilityStatement(request):
	base_url = request.build_absolute_uri("/" + API_PREFIX.strip("/"))
	return Response(build_capability_statement(base_url), status=status.HTTP_200_OK)


def registerCapabilityStatementMediator():
	register_fhir_mediator(
		"metadata",
		urn="urn:mediator:python_fhir_r4_CapabilityStatement_mediator",
		methods=("GET",),
		display_name="CapabilityStatement",
	)
