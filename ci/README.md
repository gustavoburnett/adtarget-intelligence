# CI offline

Pull requests targeting main run Python 3.12.12 / Node 22.14.0 on Ubuntu 24.04.
Actions are pinned to commit SHAs. Full git history is required by preservation tests.
Only contents:read is granted; checkout does not persist credentials. No Secrets,
Google Sheets configuration, deployment or application startup is used.

`requirements-ci.txt` pins transitive dependencies and hashes, independently of
production requirements. pandas 3.0.3 preserves the frozen-checkpoint diagnostics
asserted by the existing suite. pandas 3.1 changed the datetime any() error text;
pandas 2.3 only warns instead of raising. Neither matches that checkpoint contract.
This is a CI environment pin, not a financial logic change.

Recreate the lock from the repository root with uv 0.13.6:

    uv pip compile ci/requirements.in --python-version 3.12.12 --universal --generate-hashes -o requirements-ci.txt

Install and run:

    python -m pip install --require-hashes -r requirements-ci.txt
    python -m pip check
    python -m pytest -p ci.offline -q
    node --input-type=module -e "import {result} from './tests/carteira_deep_link.mjs'; import {specialNamesResult} from './tests/carteira_frontend.mjs'; console.log({links: result, specialNames: specialNamesResult});"

The CI-only pytest plugin blocks Python socket connections and DNS for the whole
session. Tests use synthetic fixtures and mocked loaders. The JavaScript tests
use the real inline script with a minimal DOM; they do not certify Safari,
keyboard navigation, screen-reader speech, or a physical iPhone.

Branch protection was not changed. A green run is not a publication approval.
