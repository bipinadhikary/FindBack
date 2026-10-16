# Demo recording — approximately seven minutes
Use synthetic data only. Start with README commands; open `/` and `/docs`. Rehearse first. Repeated rehearsals add reports; state the counts actually displayed.

1. **0:00–0:45:** Introduce FindBack and Bipin Adhikari as sole developer. Explain one-campus lost/found reporting; recovery verification is planned.
2. **0:45–2:00:** Create Lost / `Demo blue backpack` / Backpack / `Blue demo backpack with a yellow star` / `Demo campus library` / `2026-10-12`. Show save confirmation, list entry, details and ID.
3. **2:00–3:00:** Create Found / `Demo silver bottle` / Water bottle / `Silver demo bottle with a green leaf sticker` / `Demo student center` / `2026-10-12`. Show both entries.
4. **3:00–4:00:** Apply Lost + Backpack + search `yellow`; open details. Change to Found + Water bottle and clear search. Search `no-such-demo-item` to show empty results. Clear filters.
5. **4:00–5:00:** Show required-field browser validation. In `/docs`, POST a valid body except category `wallet` and show 422. GET `/reports/missing` and show 404.
6. **5:00–6:00:** Note report ID/title. Stop with Ctrl+C, restart with the same README command, refresh browser, show the same ID and data. Explain SQLite persistence.
7. **6:00–7:00:** Run `python scripts/verify.py` and show actual PASS output. Show current versus proposed architecture. Explain AWS, AI, authentication, photos, verification, notifications and CI/CD remain planned.

Capture real screenshots of reports, filters, details, errors and PASS logs. Do not invent evidence. Record 5–10 minutes, play it back, and confirm instructor access before submission.
