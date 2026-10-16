# Progress - October 16, 2026

**Project:** FindBack, Group 32. **Developer:** Bipin Adhikari (sole developer).

## Completed and verified

- FastAPI report creation, listing, and individual retrieval.
- SQLite persistence across real server restarts.
- Combined type/category/text filters and appropriate 422/404 responses.
- Static web interface and local launcher with browser links.
- Python 3.14.7 environment; dependency consistency check passed.
- Repeatable HTTP verification using a temporary database.
- Browser creation/filter/details/restart workflow manually confirmed by Bipin.
- Six actual screenshots supplied for the midpoint; six-slide PowerPoint with speaker notes delivered separately.
- Setup, architecture, presentation outline, demo script, and verification documentation.

See [verification.md](verification.md) for actual test results and remaining manual checks. Presentation files and screenshots are separate submission materials, not bundled in this checkout.

## Pending

- Record and review the 5-10 minute demonstration.
- Review and submit the presentation.
- Commit/push reviewed repository changes and confirm instructor access.
- Complete remaining browser edge-case, keyboard, and narrow-screen checks.
- Resolve AWS Academy Learner Lab access and verify at least one cloud feature. This requirement remains unmet.

The optional S3 backup experiment is deferred. Only local export/offline checks have passed; no AWS integration is verified.

## Challenges and decisions

The initial report implementation used memory, which lost data after restart. Built-in SQLite adds persistence without another service. A single server serves the frontend and API, keeping the project small. Virtual-environment activation differed between PowerShell and CMD, so documented launch commands now use the environment's Python directly. An occupied port can be handled with `run.py --port 8001`. Cloud lab access was not resolved, so the local prototype remains the implemented architecture.

## Completion plan and risks

| Target | Deliverable / acceptance gate |
|---|---|
| Before midpoint submission | Review presentation, record/play back demo, commit/push repository, confirm instructor access |
| Next development session | Resolve Learner Lab access; confirm allowed services, budget, and final course deadline; verify one cloud feature |
| Following milestone | Design authentication and ownership verification; validate private photo storage and preliminary category/keyword matching |
| Cloud milestone | Select compute/network entry; validate DynamoDB access patterns and S3 security; implement and verify the selected integration |
| Before final submission | End-to-end tests, recovery/access checks, match evaluation, updated documentation and final demonstration |

Dates after midpoint are provisional because the final deadline is not provided. Technical risks include cloud permissions/migration, privacy, and false matches. Resource risks include lab access and budget limits. Schedule risk is significant for a sole developer; defer semantic AI and notifications if needed to protect core reliability. Pagination, backups, migrations, monitoring, and CI/CD remain open.
