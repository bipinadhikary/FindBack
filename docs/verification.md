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
