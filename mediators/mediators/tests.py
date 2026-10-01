import importlib
import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mediators import urls


class MediatorAutoRegistrationTests(SimpleTestCase):
    def test_auto_register_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(urls.auto_register_enabled())

    def test_auto_register_enabled_by_environment_variable(self):
        for value in ("true", "TRUE", " True "):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": value}):
                    self.assertTrue(urls.auto_register_enabled())

    def test_auto_register_disabled_for_other_values(self):
        for value in ("false", "0", "", "yes"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPENHIM_AUTO_REGISTER": value}):
                    self.assertFalse(urls.auto_register_enabled())

    def test_register_mediators_calls_every_registration(self):
        registrations = [MagicMock(__name__=f"register{i}") for i in range(3)]

        urls.register_mediators(registrations)

        for register in registrations:
            register.assert_called_once_with()

    def test_register_mediators_continues_when_one_registration_fails(self):
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
            ],
        )

    def _reload_urls_with_mocked_registrations(self, env_value):
        """Recharge urls.py avec des fonctions d'enregistrement simulées."""
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
        mocks = self._reload_urls_with_mocked_registrations("false")
        for register in mocks:
            register.assert_not_called()

    def test_loading_urls_registers_every_mediator_when_enabled(self):
        mocks = self._reload_urls_with_mocked_registrations("true")
        for register in mocks:
            register.assert_called_once_with()
