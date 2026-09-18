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

- `mediators/mediators/urls.py` used to call `register*Mediator()` at import time, which hits the real DB/network as a side effect of loading URLconf — breaks `manage.py test`/`migrate`. These calls are now commented out (matches README step 7); keep them commented except for real deployments with config set.
- All 8 mediator apps (`claim_mediator`, `coverage_mediator`, `organisation_mediator`, `group_mediator`, `patient_mediator`, `contract_mediator`, `claimresponse_mediator`, `coverageeligibilityrequest_mediator`) have near-identical copy-pasted `views.py`. A bug fixed in one (e.g. query params dropped, status code not propagated, unguarded `json.loads`) likely exists in all the others — check before assuming it's isolated.
- `overview.views.configview()` returns a DRF `Response`; existing code reads it via `result.__dict__["data"]` instead of `.data` — unusual but intentional-looking pattern repeated everywhere, not a typo to "fix" in isolation.
