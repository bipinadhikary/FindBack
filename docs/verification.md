# Verification — October 16, 2026
Python 3.14.7 on Windows. Dependency check: `No broken requirements found.`

Executed `python scripts/verify.py` successfully:
```text
PASS: creation, list, detail, combined filters, empty results, validation, 404, frontend assets
PASS: both reports survive a real server restart; temporary test database only
```
Checks use a real localhost Uvicorn process and temporary SQLite file. Cover lost/found creation (201), list, exact details, combined filters, empty results, whitespace title, unsupported type/category, malformed/future date, short description, missing location, invalid category filter (422), missing report (404), HTML/JS/CSS delivery, and both reports after process restart.

## Deferred cloud experiment

Optional cloud backup preparation: a local `--dry-run` successfully exported the current database without contacting AWS. Three local backup checks cover encryption request parameters, successful byte comparison, corrupted-download rejection, stream closure, and avoiding database creation at an invalid path. These use a memory substitute for S3 and do **not** verify AWS connectivity. Live S3 upload/download remains pending.

## Browser acceptance

Bipin confirmed that the requested manual workflow works: create lost/found reports, apply filters/search, view details, and retain reports after restarting. Browser workflow confirmation is manual; automated verification covers HTTP behavior separately. Six supplied screenshots show the list, combined filters, details, invalid-category request/422 response and verification PASS output. Screenshots are separate submission materials; see presentation-evidence.md. Recording remains pending.

- [x] Create lost and found reports using the form (Bipin confirmed).
- [x] Apply type/category filters and text search (Bipin confirmed).
- [x] Open details and check saved values (Bipin confirmed).
- [ ] Check empty results and clearing filters.
- [ ] Check required-field validation and API errors.
- [x] Restart server and refresh; saved reports remain (Bipin confirmed).
- [ ] Check narrow viewport, keyboard use and visible errors.
- [x] Capture actual screenshots (six supplied by Bipin and inspected).
- [x] Demonstrate invalid-category rejection (422 shown in supplied screenshots).
- [ ] Record the working demo.
