"""django_openhim_mediators URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import logging
import os

from django.contrib import admin
from django.urls import path


from claim_mediator.views import getClaims
from coverage_mediator.views import getCoverage
from organisation_mediator.views import getOrganisation
from group_mediator.views import getGroup
from patient_mediator.views import getPatient
from contract_mediator.views import getContract
from diagnosis_mediator.views import getDiagnosis
from claimresponse_mediator.views import getClaimResponse
from coverageeligibilityrequest_mediator.views import getCoverageEligibilityRequest
from location_mediator.views import getLocation

from coverage_mediator.views import registerCoverageMediator
from claim_mediator.views import registerClaimsMediator
from organisation_mediator.views import registerOrganisationMediator
from group_mediator.views import registerGroupMediator
from patient_mediator.views import registerPatientMediator
from contract_mediator.views import registerContractMediator
from diagnosis_mediator.views import registerDiagnosisMediator
from claimresponse_mediator.views import registerClaimResponseMediator
from coverageeligibilityrequest_mediator.views import registerCoverageEligibilityRequestMediator
from location_mediator.views import registerLocationMediator

logger = logging.getLogger(__name__)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/api_fhir_r4/Claim', getClaims),
    path('api/api_fhir_r4/Coverage', getCoverage),
    path('api/api_fhir_r4/Organisation', getOrganisation),
    path('api/api_fhir_r4/Patient', getPatient),
    path('api/api_fhir_r4/Patient/<str:resource_id>', getPatient),
    path('api/api_fhir_r4/Group', getGroup),
    path('api/api_fhir_r4/Group/<str:resource_id>', getGroup),
    path('api/api_fhir_r4/Contract', getContract),
    path('api/api_fhir_r4/CodeSystem/diagnosis', getDiagnosis),
    path('api/api_fhir_r4/CodeSystem/diagnosis/<str:code>', getDiagnosis),
    path('api/api_fhir_r4/ClaimResponse', getClaimResponse),
    path('api/api_fhir_r4/ClaimResponse/<str:resource_id>', getClaimResponse),
    path('api/api_fhir_r4/CoverageEligibilityRequest', getCoverageEligibilityRequest),
    path('api/api_fhir_r4/Location', getLocation),

]

# -----------------------------------------------------------------------------
# Enregistrement des médiateurs auprès d'openHIM au démarrage
# -----------------------------------------------------------------------------
# Activé uniquement si la variable d'environnement OPENHIM_AUTO_REGISTER vaut
# "true" (positionnée dans docker-compose.yml pour les déploiements).
# Désactivé par défaut : le chargement de ce fichier par "manage.py test",
# "migrate", etc. ne doit pas contacter openHIM ni dépendre de la configuration.

MEDIATOR_REGISTRATIONS = (
    registerClaimsMediator,
    registerCoverageMediator,
    registerOrganisationMediator,
    registerGroupMediator,
    registerPatientMediator,
    registerContractMediator,
    registerDiagnosisMediator,
    registerClaimResponseMediator,
    registerCoverageEligibilityRequestMediator,
    registerLocationMediator,
)


def register_mediators(registrations=MEDIATOR_REGISTRATIONS):
    """Enregistre chaque médiateur auprès d'openHIM.

    L'échec d'un enregistrement (openHIM injoignable, configuration absente...)
    est journalisé sans empêcher les autres enregistrements ni le démarrage
    de l'application.
    """
    for register in registrations:
        try:
            register()
        except Exception:
            logger.exception(
                "Échec de l'enregistrement auprès d'openHIM : %s", register.__name__
            )


def auto_register_enabled():
    return os.environ.get("OPENHIM_AUTO_REGISTER", "false").strip().lower() == "true"


if auto_register_enabled():
    register_mediators()
