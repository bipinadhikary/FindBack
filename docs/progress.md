# Project progress

FindBack - Group 32

Bipin Adhikari, sole developer

Midpoint status: October 16, 2026

## Completed

- Lost and found report creation, browsing, filtering, and individual details.
- SQLite storage that preserves reports after restarting the server.
- Validation for report fields and appropriate 422/404 responses.
- A web interface served by FastAPI and a local launcher.
- HTTP checks covering the main workflow and restart persistence.
- Manual browser checks for creation, filters, details, and persistence.
- Screenshots and a six-slide midpoint presentation, kept separately from the repository.

## Remaining work

- Finish the demo recording and submission review.
- Confirm instructor access to the GitHub repository.
- Resolve AWS Academy Learner Lab access and verify a cloud integration.
- Add authentication and ownership verification.
- Add private photo uploads and preliminary category/keyword matching.
- Evaluate semantic matching after the basic workflow is reliable.

Cloud integration, semantic AI, notifications, and CI/CD are not implemented. The S3 backup script is an experiment with local checks only.

## Challenges

The first report implementation used memory, so restarting lost the reports. SQLite provides persistence without another service. PowerShell and CMD activate virtual environments differently; the setup commands now call the environment's Python directly. An occupied server port can be handled with `run.py --port 8001`. Learner Lab access still needs to be resolved.

## Completion plan

| Stage | Work |
|---|---|
| Midpoint submission | Review slides, record and play back the demo, update GitHub, check instructor access |
| Next session | Resolve Learner Lab access, check allowed services and budget, verify one cloud feature |
| Next milestone | Implement identity/ownership controls, private photos, and basic matching |
| Before final submission | Test the full workflow, review permissions and matching quality, update documentation |

The final course deadline still needs confirmation. Technical risks include cloud permissions, storage migration, privacy, and false matches. Resource risks are lab access and budget limits. As a sole developer, optional AI and notification work may need to be deferred to keep the core features reliable.
