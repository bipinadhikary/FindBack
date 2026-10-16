# Demo walkthrough

Target length: 6-8 minutes. Use synthetic reports. Start the application from the project folder:

```text
.\.venv\Scripts\python.exe run.py --port 8001
```

Open http://127.0.0.1:8001 and http://127.0.0.1:8001/docs. Keep another terminal available for verification. Record a short microphone test first.

## 0:00-0:40: Introduction

Introduce FindBack, Group 32, and Bipin Adhikari as the sole developer. Explain the campus lost-and-found problem and the initial scope: backpacks, water bottles, and headphones.

## 0:40-2:00: Create reports

Create a lost report: Demo blue backpack, category Backpack, description Blue demo backpack with a yellow star, location Demo campus library, today's date. Save and show the list entry.

Create a found report for a silver water bottle with a green sticker at the Demo student center. Show the confirmation and new entry.

## 2:00-3:00: Filters and details

Apply Lost + Backpack + search yellow. Open the matching report and explain its fields and ID. Search no-such-demo-item to show empty results, then clear filters.

## 3:00-4:15: Validation

In API documentation, use POST /reports with the sample body in [api.md](api.md), changing category to wallet. Show the actual 422 response and accepted categories. Use GET /reports/{report_id} with missing as the ID to show 404.

## 4:15-5:15: Persistence

Note a report ID. Stop the server with Ctrl+C, restart with the same command, and refresh the browser. Open the same report and show that its data and ID remain. Explain that SQLite stores reports on disk.

## 5:15-6:15: Verification

Run in the second terminal:

```text
.\.venv\Scripts\python.exe scripts\verify.py
```

Show both PASS lines. Explain that the checks use a temporary database and include a real process restart.

## 6:15-7:00: Architecture and next steps

Explain FastAPI/Uvicorn, the static frontend, and local SQLite. Describe cloud integration, authentication, ownership verification, photos, and matching as remaining work. The first cloud milestone is resolving Learner Lab access and verifying a real integration.

Play back the finished recording to check sound, readable text, and duration before submitting.
