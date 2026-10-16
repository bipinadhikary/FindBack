# Report API

The API runs on the same localhost address as the web interface. Interactive documentation is available at `/docs` while the server is running.

| Method | Path | Result |
|---|---|---|
| GET | `/` | Web interface |
| GET | `/health` | Process status; does not check database availability |
| POST | `/reports` | Create report, returns 201 |
| GET | `/reports` | List reports, optionally filtered |
| GET | `/reports/{report_id}` | Report details, or 404 if missing |

## Create a report

```json
{
  "report_type": "lost",
  "title": "Demo blue backpack",
  "category": "backpack",
  "description": "Blue demo backpack with a yellow star",
  "location": "Demo campus library",
  "date": "2026-10-12"
}
```

Required fields:

- `report_type`: lost or found.
- `title`: 3-100 characters.
- `category`: backpack, water bottle, or headphones.
- `description`: 10-2000 characters.
- `location`: 2-200 characters.
- `date`: valid date, no later than the server's local date.

Text is trimmed. Invalid, missing, or unexpected body fields return 422. The response includes a generated `id` and status `open`. Editing and resolving reports are not implemented.

## Filter reports

`GET /reports?report_type=lost&category=backpack&q=yellow`

All filters are optional and can be combined. Search checks title, description, and location using SQLite's case mapping. Unsupported type/category values return 422. No matches returns an empty list. Reports are ordered by event date descending, then insertion order descending.

## Storage

Reports are stored in `data/findback.sqlite3`. Startup creates the database and table if needed. `FINDBACK_DB_PATH` optionally overrides the path. Local databases are excluded from Git. The prototype has no authentication and is intended for localhost use with synthetic data.
