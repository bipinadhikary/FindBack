# Deployment and operations

The final deployment runs on Ubuntu EC2 t3.micro in us-east-2 with a 15 GiB EBS disk. Nginx terminates HTTPS. The systemd findback service runs Uvicorn on 127.0.0.1:8000. No credentials or application database are included here.

## Setup outline

1. Copy the source to an Ubuntu server with Python 3.12, create a virtual environment, and install requirements.txt.
2. Choose a persistent database path outside replaceable code directories. Set FINDBACK_DB_PATH to that absolute path in the service environment.
3. Configure systemd to run the virtual environment's Python with `-m uvicorn main:app --host 127.0.0.1 --port 8000`, using the project working directory and an unprivileged account.
4. Configure Nginx to proxy to http://127.0.0.1:8000. Forward Host and X-Forwarded-Proto. Allow report uploads with client_max_body_size 20m.
5. Configure trusted HTTPS. This deployment used Certbot webroot validation and a Let's Encrypt short-lived IP certificate. Keep the challenge directory reachable on HTTP 80 and reload Nginx with a renewal deploy hook.
6. Redirect HTTP to HTTPS except for certificate validation. Set FINDBACK_SECURE_COOKIE=1 for the application service.
7. Allow public TCP 80/443 in the security group. Restrict TCP 22 to the administrator's IP and leave 8000 closed publicly.
8. Enable services at boot. Verify HTTPS, health, unauthenticated browsing rejection, HTTP redirection, and certificate renewal with a dry-run.

For local HTTP, leave FINDBACK_SECURE_COOKIE unset. The local runner binds only to loopback.

## Updates and recovery

Before replacing code, take a complete SQLite snapshot using scripts/backup_database.py and preserve the previous release. Keep the original persistent database path. Run tests on temporary data, switch the service, and verify health. For rollback, preserve newer data before restoring compatible code and database together.

Local snapshots do not protect against loss of the entire volume. Off-instance backups are future work. Never commit databases, snapshots, environment secrets, or SSH keys.

The public IP may change after EC2 stop/start. If it changes, update redirects and issue a certificate for the new address. Keep renewal active. Stopping EC2 makes the website unavailable; termination can delete volumes depending on their settings.
