# Group 32: FindBack midpoint presentation — six slides, about five minutes
The six-slide PowerPoint with speaker notes was delivered separately as Group32-FindBack.pptx and is not bundled in this checkout. Assigned group: 32. Required final filename: `Group32-FindBack.pptx`. See presentation-evidence.md for the supplied screenshot index. Timings include pointing to diagrams/evidence.

## 1. FindBack — campus lost and found (0:00–0:40)
Slide: Bipin Adhikari, sole developer. Audience: students and campus staff. Problem: scattered lost-item information. Solution: structured campus reporting and browsing. Initial scope: backpacks, water bottles, headphones.

Speaker notes: “FindBack is my Cloud Computing course project, and I am the sole developer. Students who lose belongings need a consistent way to describe what is missing and check what others have found. My project brings those reports into a single campus view. I limited the initial categories to keep the first version manageable. The midpoint focuses on a usable reporting workflow. Matching and safe item recovery are later milestones rather than features I claim to have completed.”

## 2. Working prototype (0:40–1:30)
Slide: Create lost/found reports; browse and filter; view details; persistent storage; validation. Use Screenshot (11), with Screenshot (12) and Screenshot (13) as supporting evidence.

Speaker notes: “A report contains its type, title, category, description, location and date. The backend rejects unsupported values, missing or short text, and future dates. The interface is designed to submit the form to the API, show reports, apply combined filters and open individual details. The report ID makes it possible to retrieve the same record later. SQLite stores reports permanently across server restarts. All demonstration records are synthetic. I confirmed the core browser workflow manually: creation, filtering, details and persistence after restart. Six real screenshots have been captured; the demo recording remains pending.”

## 3. Local architecture and development practices (1:30–2:20)
Slide: Insert current diagram from architecture.md. FastAPI/Uvicorn, Pydantic, sqlite3, same-origin frontend. Git, isolated environment, pinned dependencies, repeatable verification.

Speaker notes: “One Python server serves both the web interface and the JSON API. This avoids a separate frontend build process. Pydantic handles validation, and parameterized SQLite queries store the reports. SQLite is built into Python, so persistence does not require another service. I use a virtual environment and pinned requirements to make setup repeatable. Git tracks source changes while databases and secrets stay excluded. The verification script starts an actual server with a temporary database and tests HTTP behavior. A continuous integration pipeline is not implemented.”

## 4. Cloud architecture — proposed (2:20–3:10)
Slide: Insert proposed diagram from architecture.md. FastAPI compute hosting, HTTPS/API entry, DynamoDB metadata candidate, private S3 images, possible AI processing and notifications. All planned.

Speaker notes: “The working prototype is local, and this diagram is a proposal. Compute would host FastAPI, while network entry would provide HTTPS and controlled API access. DynamoDB is a candidate for report metadata, but requires access-pattern and index design. S3 is a candidate for private photos. Matching might run asynchronously and later trigger notifications. These are decisions to validate, not existing integrations. I need to confirm the authorized AWS account, cost limits and security design before deployment. No AWS deployment or AI functionality is claimed at this midpoint. The requirement for an implemented cloud feature remains unmet; cloud work is deferred until Learner Lab access is resolved.”

## 5. Evidence, milestones and challenges (3:10–4:05)
Slide: Actual PASS output from verification.md; supplied Screenshot (15) and Screenshot (16). Completed: persistence, report API, filters, frontend source, documentation. Challenges: storage lifecycle, environment restrictions, browser verification.

Speaker notes: “The automated checks passed creation, listing, retrieval, combined filtering, empty results, input rejection, missing-report errors and static asset delivery. Both synthetic reports survived a real server process restart. These checks use a temporary database and leave the demonstration data alone. The main implementation challenge was replacing temporary memory storage while keeping the project understandable. I resolved virtual-environment activation and occupied-port setup issues, then manually checked and confirmed the core browser workflow. My screenshots show the running application, a real 422 response for the unsupported wallet category, and both verification PASS lines.”

## 6. Completion plan and risks (4:05–5:00)
Slide: Before submission: presentation review, recording, repository update/access. Next session: resolve Learner Lab access and verify one cloud feature. Next: identity/ownership, photos, preliminary matching, authorized cloud validation. Risks: schedule, costs, access control, match accuracy.

Speaker notes: “My immediate goal is to capture the working demonstration, complete the remaining acceptance checks and make the reviewed repository accessible to the instructor. Next I will design authentication and ownership verification before using real student information. Photos and preliminary category-and-keyword matching can follow. That matching must be labeled rule-based; semantic AI remains future work. Cloud integration needs separate validation. The risks are schedule pressure, cost and permissions, privacy and false matches. I will confirm the final course deadline and prioritize a complete, reliable workflow before adding optional features.”
