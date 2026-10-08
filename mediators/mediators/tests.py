"""Tests de l'enregistrement automatique des médiateurs auprès d'openHIM.

Ces tests couvrent le bloc de démarrage de ``mediators/urls.py`` :

- l'activation par la variable d'environnement ``OPENHIM_AUTO_REGISTER`` ;
- l'appel de chaque fonction d'enregistrement par ``register_mediators`` ;
- la tolérance aux échecs (un médiateur en erreur n'empêche pas les autres) ;
- le comportement réel au chargement du module ``urls.py``.

Aucun test ne contacte openHIM : toutes les fonctions d'enregistrement sont
remplacées par des simulations (``MagicMock``).
"""

import importlib
import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mediators import urls


class MediatorAutoRegistrationTests(SimpleTestCase):
    """Vérifie l'enregistrement automatique des médiateurs défini dans ``urls.py``."""

    def test_auto_register_disabled_by_default(self):
        """Sans variable ``OPENHIM_AUTO_REGISTER``, l'enregistrement est désactivé.

        Garantit que ``manage.py test``, ``migrate`` et la CI ne contactent
        jamais openHIM lorsque rien n'est configuré.
        """
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(urls.auto_register_enabled())

    def test_auto_register_enabled_by_environment_variable(self):
        """La valeur « true » active l'enregistrement, quelle que soit la casse.

        Les espaces autour de la valeur sont ignorés (``" True "`` est accepté).
        """
        for value in ("true", "TRUE", " True "):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": value}):
                    self.assertTrue(urls.auto_register_enabled())

    def test_auto_register_disabled_for_other_values(self):
        """Toute valeur autre que « true » laisse l'enregistrement désactivé.

        Évite qu'une valeur ambiguë (``"0"``, ``"yes"``, chaîne vide...)
        déclenche par erreur un enregistrement auprès d'openHIM.
        """
        for value in ("false", "0", "", "yes"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": value}):
                    self.assertFalse(urls.auto_register_enabled())

    def test_register_mediators_calls_every_registration(self):
        """``register_mediators`` appelle une fois chaque fonction d'enregistrement fournie."""
        registrations = [MagicMock(__name__=f"register{i}") for i in range(3)]

        urls.register_mediators(registrations)

        for register in registrations:
            register.assert_called_once_with()

    def test_register_mediators_continues_when_one_registration_fails(self):
        """L'échec d'un enregistrement est journalisé sans bloquer les suivants.

        Simule un openHIM injoignable pour le deuxième médiateur : le premier
        et le troisième doivent tout de même être enregistrés, et l'erreur doit
        apparaître dans les journaux avec le nom de la fonction en échec.
        """
        failing = MagicMock(__name__="registerFailing", side_effect=Exception("openHIM down"))
        ok_before = MagicMock(__name__="registerBefore")
        ok_after = MagicMock(__name__="registerAfter")

        with self.assertLogs("mediators.urls", level="ERROR") as logs:
            urls.register_mediators([ok_before, failing, ok_after])

        ok_before.assert_called_once_with()
        failing.assert_called_once_with()
        ok_after.assert_called_once_with()
        self.assertIn("registerFailing", logs.output[0])

    def test_all_mediators_are_registered(self):
        """``MEDIATOR_REGISTRATIONS`` contient les 10 médiateurs, dans l'ordre attendu.

        Protège contre l'oubli d'un médiateur lors d'une modification de ``urls.py`` :
        tout ajout ou retrait doit être reporté dans ce test.
        """
        names = [register.__name__ for register in urls.MEDIATOR_REGISTRATIONS]
        self.assertEqual(
            names,
            [
                "registerClaimsMediator",
                "registerCoverageMediator",
                "registerOrganisationMediator",
                "registerGroupMediator",
                "registerPatientMediator",
                "registerContractMediator",
                "registerClaimResponseMediator",
                "registerCoverageEligibilityRequestMediator",
                "registerLocationMediator",
                "registerDiagnosisMediator",
                "registerActivityDefinitionMediator",
            ],
        )

    def _reload_urls_with_mocked_registrations(self, env_value):
        """Recharge ``urls.py`` avec des fonctions d'enregistrement simulées.

        Remplace les 10 fonctions ``register*Mediator`` dans leurs modules
        d'origine, puis recharge ``urls.py`` avec ``OPENHIM_AUTO_REGISTER``
        positionnée à ``env_value``, ce qui ré-exécute le bloc de démarrage.

        Après le rechargement, les vraies fonctions sont restaurées et
        ``urls.py`` est rechargé une seconde fois, enregistrement désactivé,
        pour ne pas affecter les autres tests.

        Args:
            env_value: valeur donnée à ``OPENHIM_AUTO_REGISTER`` pendant le rechargement.

        Returns:
            La liste des 10 simulations, dans l'ordre de ``MEDIATOR_REGISTRATIONS``,
            pour vérifier lesquelles ont été appelées.
        """
        targets = [
            ("claim_mediator.views", "registerClaimsMediator"),
            ("coverage_mediator.views", "registerCoverageMediator"),
            ("organisation_mediator.views", "registerOrganisationMediator"),
            ("group_mediator.views", "registerGroupMediator"),
            ("patient_mediator.views", "registerPatientMediator"),
            ("contract_mediator.views", "registerContractMediator"),
            ("claimresponse_mediator.views", "registerClaimResponseMediator"),
            ("coverageeligibilityrequest_mediator.views", "registerCoverageEligibilityRequestMediator"),
            ("location_mediator.views", "registerLocationMediator"),
            ("diagnosis_mediator.views", "registerDiagnosisMediator"),
            ("activitydefinition_mediator.views", "registerActivityDefinitionMediator"),
        ]
        mocks = []
        patchers = []
        for module, name in targets:
            patcher = patch(f"{module}.{name}", MagicMock(__name__=name))
            mocks.append(patcher.start())
            patchers.append(patcher)
        try:
            with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": env_value}):
                importlib.reload(urls)
        finally:
            for patcher in patchers:
                patcher.stop()
            # Restaure urls.py avec les vraies fonctions, sans enregistrement
            with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": "false"}):
                importlib.reload(urls)
        return mocks

    def test_loading_urls_does_not_register_when_disabled(self):
        """Charger ``urls.py`` avec l'enregistrement désactivé n'appelle aucun médiateur.

        Reproduit la situation de la CI : le chargement des URL ne doit
        déclencher aucun appel vers openHIM.
        """
        mocks = self._reload_urls_with_mocked_registrations("false")
        for register in mocks:
            register.assert_not_called()

    def test_loading_urls_registers_every_mediator_when_enabled(self):
        """Charger ``urls.py`` avec l'enregistrement activé enregistre les 10 médiateurs.

        Reproduit le démarrage sur le serveur (``OPENHIM_AUTO_REGISTER=true``
        dans ``docker-compose.yml``) : chaque médiateur doit être enregistré
        exactement une fois.
        """
        mocks = self._reload_urls_with_mocked_registrations("true")
        for register in mocks:
            register.assert_called_once_with()
