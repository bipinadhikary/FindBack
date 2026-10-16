# Verification

Environment checked on October 16, 2026: Windows, Python 3.14.7. `pip check` reported no broken requirements.

## Automated checks

From the project folder on Windows:

```text
.\.venv\Scripts\python.exe scripts\verify.py
```

On macOS, with the virtual environment active:

```sh
python scripts/verify.py
```

The last successful run produced:

```text
PASS: creation, list, detail, combined filters, empty results, validation, 404, frontend assets
PASS: both reports survive a real server restart; temporary test database only
```

The script checks lost/found creation (201), listing, exact detail retrieval, combined filters, empty results, invalid/missing fields (422), a missing report (404), and HTML/CSS/JavaScript delivery. It stops and restarts a real server and checks that both reports remain. Tests use a temporary database and do not modify local demo reports.

## Manual checks

Report creation, type/category/text filters, details, and persistence after restart were checked in the browser. Screenshots show the list, filtered results, details, an unsupported-category request and its 422 response, and verification PASS output. See the [evidence index](presentation-evidence.md).

Still to check: clearing filters after empty results, required-field messages, keyboard navigation, narrow-screen layout, and recording playback.

## S3 experiment

```text
.\.venv\Scripts\python.exe scripts\test_cloud_backup.py
```

All three offline tests passed. They check upload parameters, matching downloaded bytes, corruption detection, stream closure, and avoiding database creation at an invalid path. The local export dry run also passed. These checks do not contact AWS; live S3 upload/download remains unverified.
