# Optional Amazon S3 backup - deferred

Status: deferred experiment. These instructions and the script prepare a later milestone; no live AWS integration has been verified. This experiment is not required to run the local application.

The local report database remains SQLite. `scripts/cloud_backup.py` exports reports as JSON, uploads to an existing S3 bucket with SSE-S3 encryption, downloads that exact object, and compares its bytes. It never restores or replaces the database. A successful run is a real cloud backup/retrieval demonstration; it is not cloud application hosting or a cloud primary database.

## 1. Confirm lab access

Start the instructor-provided AWS Academy Learner Lab, open its AWS Console, and confirm the region and S3 access. Check the remaining lab budget and course rules. Only use this authorized lab account. Permissions and service availability depend on the lab; enrollment alone does not establish them.

Create a general-purpose S3 bucket in an allowed region with a unique name. Keep **all Block Public Access settings on**, ACLs disabled (bucket owner enforced), and default SSE-S3 encryption. Do not enable website hosting or public policies. Record the actual bucket name and region. This script does not create buckets or change access policies.

## 2. Configure temporary credentials locally

Use AWS Details in the lab to locate the current programmatic credentials. Labels may vary. Do not paste credentials into chat, source files, screenshots, or Git. In your user home directory, use the AWS shared credentials file (`%USERPROFILE%\.aws\credentials` on Windows, `~/.aws/credentials` on Mac). Add a named profile without replacing other profiles:

```ini
[findback-lab]
aws_access_key_id = YOUR_LAB_ACCESS_KEY
aws_secret_access_key = YOUR_LAB_SECRET_KEY
aws_session_token = YOUR_LAB_SESSION_TOKEN
```

These are placeholders; enter actual temporary values only in that local file. The session token is required. Refresh the profile when credentials expire. The script explicitly selects `findback-lab` by default; it does not use a personal default profile. Keep the lab active during verification.

## 3. Run from PowerShell or CMD

Install optional cloud dependencies in the existing environment:

```text
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
.\.venv\Scripts\python.exe scripts\cloud_backup.py --dry-run
```

Review reports first and use synthetic data only. Substitute the actual lab bucket and region:

```text
.\.venv\Scripts\python.exe scripts\cloud_backup.py --bucket YOUR_BUCKET --region YOUR_REGION --synthetic-data-only
```

Mac with environment active: use `python scripts/cloud_backup.py` with the same arguments. No AWS CLI is required. The database must already exist (start FindBack and create synthetic reports first).

## 4. Demonstrate and report accurately

Only after the live command prints PASS, record the S3 path and SHA-256 output, show the object in the S3 Console, and capture screenshots excluding credentials. Show that the downloaded contents matched the uploaded export. Unique object names avoid replacing earlier backups. This is an operator-run backup, not an automatic or web-interface feature. Failed download verification can leave an uploaded object; inspect the reported errors before retrying. Follow lab/instructor retention and cleanup instructions.

Live AWS verification is pending. Do not update midpoint claims to completed until upload/download actually succeeds. No bucket has been created by this implementation work.

References: [AWS credentials profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html), [S3 PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html).
