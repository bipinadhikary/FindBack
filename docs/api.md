# API

Run the application and open `/docs` for request schemas and interactive documentation. Application routes require sign-in. Writes use JSON, same-origin checks, and the session CSRF token. See static/app.js for request headers.

| Method | Route | Purpose |
|---|---|---|
| GET | /health | Process health |
| POST | /auth/register | Register |
| POST | /auth/login | Sign in |
| GET | /auth/me | Current account |
| POST | /auth/logout | End session |
| GET, POST | /reports | Browse/create reports |
| GET | /reports/{report_id} | Report detail |
| GET | /reports/{report_id}/photos/{photo_id} | Protected photo |
| POST | /reports/{report_id}/conversations | Open private conversation |
| GET | /conversations | Participant inbox |
| GET, POST | /conversations/{conversation_id}/messages | Read/send messages |
| POST | /conversations/{conversation_id}/read | Mark read |
| POST | /reports/{report_id}/claims | Submit claim |
| GET | /claims | Accessible claims |
| POST | /claims/{claim_id}/actions | Decision, withdrawal, handover |
| GET | /matches | Possible matches |
| GET | /notifications | Recipient notifications |
| POST | /notifications/read-all | Mark read through a boundary |
| POST | /notifications/{notification_id}/read | Mark one read |
| GET | /admin/users | Role management |
| PATCH | /admin/users/{user_id}/role | Assign/remove reception role |

Ownership and participant checks restrict claims and chats. Administrator status does not grant unrestricted access to private conversations. Startup migrations retain existing records; legacy ownerless reports have limited interaction support.
