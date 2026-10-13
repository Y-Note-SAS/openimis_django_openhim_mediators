"""Tests du client openHIM (authentification, enregistrement, heartbeat).

Aucun appel réseau : ``requests.post``, ``uptime`` et le scheduler sont simulés.
"""

import base64
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from openhim_mediator_utils.auth import Auth
from openhim_mediator_utils.heartbeat import Heartbeat
from openhim_mediator_utils.main import Main
from openhim_mediator_utils.mediator_registration import MediatorRegistration

OPTIONS = {
    "verify_cert": False,
    "apiURL": "https://openhim.local:8080",
    "username": "root@openhim.org",
    "password": "pass",
    "force_config": False,
    "interval": 5,
}
CONF = {"urn": "urn:mediator:test"}


def response(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


class AuthTests(SimpleTestCase):
    def test_gen_auth_headers_is_basic_auth(self):
        headers = Auth(OPTIONS).gen_auth_headers()
        expected = base64.b64encode(b"root@openhim.org:pass").decode()
        self.assertEqual(headers, {"Authorization": "Basic " + expected})

    def test_authenticate_disables_warnings_when_cert_not_verified(self):
        with patch("openhim_mediator_utils.auth.urllib3.disable_warnings") as disable:
            self.assertEqual(Auth(OPTIONS).authenticate(), {})
        disable.assert_called_once()

    def test_authenticate_keeps_warnings_when_cert_verified(self):
        with patch("openhim_mediator_utils.auth.urllib3.disable_warnings") as disable:
            Auth(dict(OPTIONS, verify_cert=True)).authenticate()
        disable.assert_not_called()


class MediatorRegistrationTests(SimpleTestCase):
    def _registration(self, verify_cert=False):
        auth = MagicMock()
        auth.gen_auth_headers.return_value = {"Authorization": "Basic x"}
        options = {
            "mediators_url": "https://openhim.local:8080/mediators",
            "verify_cert": verify_cert,
            "force_config": False,
        }
        return MediatorRegistration(auth=auth, conf=CONF, options=options), auth

    def test_run_posts_conf_to_openhim(self):
        registration, auth = self._registration()
        with patch(
            "openhim_mediator_utils.mediator_registration.requests.post",
            return_value=response(201),
        ) as post:
            registration.run()
        auth.authenticate.assert_called_once_with()
        post.assert_called_once_with(
            url="https://openhim.local:8080/mediators",
            json=CONF,
            headers={"Authorization": "Basic x"},
            verify=False,
        )

    def test_run_raises_on_401(self):
        registration, _ = self._registration()
        with patch(
            "openhim_mediator_utils.mediator_registration.requests.post",
            return_value=response(401),
        ):
            with self.assertRaisesMessage(Exception, "Authentication failed"):
                registration.run()

    def test_run_raises_on_unexpected_status(self):
        registration, _ = self._registration()
        with patch(
            "openhim_mediator_utils.mediator_registration.requests.post",
            return_value=response(500),
        ):
            with self.assertRaisesMessage(Exception, "500"):
                registration.run()

    def test_run_keeps_warnings_when_cert_verified(self):
        registration, _ = self._registration(verify_cert=True)
        with patch(
            "openhim_mediator_utils.mediator_registration.requests.post",
            return_value=response(201),
        ), patch(
            "openhim_mediator_utils.mediator_registration.urllib3.disable_warnings"
        ) as disable:
            registration.run()
        disable.assert_not_called()


class HeartbeatTests(SimpleTestCase):
    def setUp(self):
        self.auth = MagicMock()
        self.auth.gen_auth_headers.return_value = {"Authorization": "Basic x"}
        self.scheduler = MagicMock()

    def _heartbeat(self, **option_overrides):
        return Heartbeat(
            self.auth,
            options=dict(OPTIONS, **option_overrides),
            conf=CONF,
            scheduler=self.scheduler,
        )

    def _send(self, heartbeat, status=200, **kwargs):
        with patch(
            "openhim_mediator_utils.heartbeat.requests.post",
            return_value=response(status),
        ) as post, patch("openhim_mediator_utils.heartbeat.uptime", return_value=42.0):
            heartbeat._send(**kwargs)
        return post

    def test_send_posts_uptime_to_mediator_heartbeat_url(self):
        post = self._send(self._heartbeat())
        kwargs = post.call_args.kwargs
        self.assertEqual(
            kwargs["url"],
            "https://openhim.local:8080/mediators/urn:mediator:test/heartbeat",
        )
        self.assertEqual(kwargs["json"], {"uptime": 42.0})
        self.assertEqual(kwargs["headers"], {"Authorization": "Basic x"})
        self.assertFalse(kwargs["verify"])

    def test_send_requests_config_when_forced(self):
        post = self._send(self._heartbeat(), force_config=True)
        self.assertEqual(post.call_args.kwargs["json"], {"uptime": 42.0, "config": True})

    def test_send_requests_config_when_option_force_config(self):
        post = self._send(self._heartbeat(force_config=True))
        self.assertTrue(post.call_args.kwargs["json"]["config"])

    def test_send_raises_on_non_200(self):
        with self.assertRaisesMessage(Exception, "500"):
            self._send(self._heartbeat(), status=500)

    def test_send_keeps_warnings_when_cert_verified(self):
        with patch("openhim_mediator_utils.heartbeat.urllib3.disable_warnings") as disable:
            self._send(self._heartbeat(verify_cert=True))
        disable.assert_not_called()

    def test_activate_schedules_job_once(self):
        heartbeat = self._heartbeat()
        heartbeat.activate()
        heartbeat.activate()
        self.scheduler.add_job.assert_called_once_with(
            heartbeat._send, "interval", seconds=5
        )
        self.scheduler.start.assert_called_once_with()

    def test_activate_defaults_to_10_seconds_without_interval(self):
        heartbeat = self._heartbeat(interval=None)
        heartbeat.activate()
        self.assertEqual(self.scheduler.add_job.call_args.kwargs["seconds"], 10)

    def test_deactivate_removes_job_only_when_active(self):
        heartbeat = self._heartbeat()
        heartbeat.deactivate()  # rien à retirer
        heartbeat.activate()
        heartbeat.deactivate()
        self.scheduler.add_job.return_value.remove.assert_called_once_with()

    def test_fetch_config_authenticates_and_forces_config(self):
        heartbeat = self._heartbeat()
        with patch.object(heartbeat, "_send", return_value="cfg") as send:
            self.assertEqual(heartbeat.fetch_config(), "cfg")
        self.auth.authenticate.assert_called_once_with()
        send.assert_called_once_with(True)


class MainTests(SimpleTestCase):
    def setUp(self):
        patcher = patch("openhim_mediator_utils.main.BackgroundScheduler")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.main = Main(options=OPTIONS, conf=CONF)

    def test_builds_mediators_url_from_api_url(self):
        self.assertEqual(
            self.main.mediator_registration.options["mediators_url"],
            "https://openhim.local:8080/mediators",
        )

    def test_delegates_to_collaborators(self):
        self.main.auth = MagicMock()
        self.main.mediator_registration = MagicMock()
        self.main.heartbeat = MagicMock()

        self.main.authenticate()
        self.main.gen_auth_headers()
        self.main.register_mediator()
        self.main.activate_heartbeat()
        self.main.deactivate_heartbeat()
        self.main.fetch_config()

        self.main.auth.authenticate.assert_called_once_with()
        self.main.auth.gen_auth_headers.assert_called_once_with()
        self.main.mediator_registration.run.assert_called_once_with()
        self.main.heartbeat.activate.assert_called_once_with()
        self.main.heartbeat.deactivate.assert_called_once_with()
        self.main.heartbeat.fetch_config.assert_called_once_with()
