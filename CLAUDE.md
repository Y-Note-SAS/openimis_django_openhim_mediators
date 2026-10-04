# openimis_django_openhim_mediators

Django app exposing FHIR R4 mediators between openHIM and openIMIS. Python 3.12 (see `Dockerfile`).

## Running tests

No local venv in this repo — validate via Docker:
```
docker build -t mediators-test -q . && docker run --rm mediators-test python manage.py test
docker rmi mediators-test
```
Single app: `... python manage.py test patient_mediator`. CI runs the same command from `mediators/` on every push/PR (`.github/workflows/tests.yml`).

## Gotchas

- `mediators/mediators/urls.py` registers the mediators with openHIM at import time **only when `OPENHIM_AUTO_REGISTER=true`** (set in `docker-compose.yml`). It is off by default so `manage.py test`/`migrate` (and CI) never hit the DB/network while loading the URLconf. Each registration is wrapped in try/except: one failure is logged and does not block the others or the app startup. Covered by `mediators/mediators/tests.py`.
- The mediator apps (`claim`, `coverage`, `organisation`, `group`, `patient`, `contract`, `claimresponse`, `coverageeligibilityrequest`, `location`) are thin: each `views.py` only declares its `@api_view` and calls `overview.fhir_proxy.proxy_fhir_request` / `register_fhir_mediator`. Request forwarding (query params, status propagation, 502 on non-JSON) and openHIM registration live once in `mediators/overview/fhir_proxy.py`; fix bugs there. Tests of each view patch `overview.fhir_proxy.configview` and `overview.fhir_proxy.requests.request`.
- `overview.views.configview()` returns a DRF `Response`; existing code reads it via `result.__dict__["data"]` instead of `.data` — unusual but intentional-looking pattern repeated everywhere, not a typo to "fix" in isolation.
