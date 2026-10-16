"""Export synthetic reports and verify a private S3 backup by downloading it."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def export_reports(database):
    # Read-only mode avoids accidentally creating an empty database at a typo path.
    connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        reports = [dict(row) for row in connection.execute(
            'SELECT id, report_type, title, category, description, location, date, status '
            'FROM reports ORDER BY id')]
    finally:
        connection.close()
    document = {
        'schema_version': 1,
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'reports': reports,
    }
    return json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8'), len(reports)


def upload_and_verify(client, bucket, key, payload):
    digest = hashlib.sha256(payload).hexdigest()
    client.put_object(Bucket=bucket, Key=key, Body=payload,
                      ContentType='application/json', ServerSideEncryption='AES256',
                      Metadata={'sha256': digest})
    response = client.get_object(Bucket=bucket, Key=key)
    stream = response['Body']
    try:
        downloaded = stream.read()
    finally:
        stream.close()
    if downloaded != payload:
        raise RuntimeError('Downloaded backup differs from the export; verification failed')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path(os.environ.get(
        'FINDBACK_DB_PATH', str(ROOT / 'data' / 'findback.sqlite3'))))
    parser.add_argument('--bucket', help='existing private S3 bucket in your Learner Lab')
    parser.add_argument('--region', help='region containing that bucket')
    parser.add_argument('--profile', default='findback-lab', help='AWS profile (default: findback-lab)')
    parser.add_argument('--synthetic-data-only', action='store_true',
                        help='confirm this database contains only synthetic demo reports')
    parser.add_argument('--dry-run', action='store_true', help='export locally without contacting AWS')
    args = parser.parse_args()
    if not args.dry_run and not args.synthetic_data_only:
        parser.error('Review your reports, then supply --synthetic-data-only for the demo upload')
    if not args.dry_run and (not args.bucket or not args.region):
        parser.error('--bucket and --region are required for an S3 upload')
    try:
        payload, count = export_reports(args.database)
        if args.dry_run:
            print(f'LOCAL CHECK ONLY: exported {count} report(s), {len(payload)} bytes. No AWS request made.')
            return 0
        try:
            import boto3
        except ImportError:
            raise RuntimeError('Install cloud dependencies: python -m pip install -r requirements-cloud.txt') from None
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        client = session.client('s3')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        key = f'findback/backups/{stamp}-{uuid4().hex}.json'
        digest = upload_and_verify(client, args.bucket, key, payload)
        print(f'PASS: uploaded and downloaded {count} report(s); contents match exactly.')
        print(f'S3 object: s3://{args.bucket}/{key}')
        print(f'SHA-256: {digest}')
        print('Primary database remains local SQLite. This verifies backup retrieval, not database restoration.')
        return 0
    except Exception as error:
        print(f'Backup failed: {error}', file=sys.stderr)
        print('Check the database path, active Learner Lab session, temporary credentials, '
              'bucket region, and S3 PutObject/GetObject permissions.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
