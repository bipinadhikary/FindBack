# Verification

Run the scripts in the README with dependencies installed. Tests create temporary databases and isolated server processes, rather than modifying live data.

| Script | Coverage |
|---|---|
| verify.py | Accounts, reports, photos, validation, migration, roles, sessions, CSRF, throttling |
| test_chat.py | Private chat, participant permissions, read state, persistence |
| test_claims.py | Finder/reception actions, handover, withdrawal, competing claims |
| test_matching.py | Matching rules, exclusions, lifecycle |
| test_activity.py | Recipient-scoped notifications, pagination, read state |
| test_database_backup.py | Full SQLite backup checks |
| test_cloud_backup.py | Legacy reports export using mock S3; no AWS calls |

On November 12, 2026, deployment checks verified HTTPS homepage 200, health status ok, unauthenticated reports 401, HTTP-to-HTTPS redirect 301, and a successful certificate renewal dry-run. Workflow and persistence checks passed during deployment.

These are dated functional observations, not uptime or capacity guarantees. No controlled load test, response-time benchmark, or matching-accuracy study has been performed.

Final repository verification on November 26, 2026: all seven listed scripts passed in a fresh Python 3.12.14 virtual environment using requirements.txt. No production database was used.
