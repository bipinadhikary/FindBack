"""Local checks only; these tests never contact AWS."""
from io import BytesIO
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cloud_backup import export_reports, upload_and_verify


class MemoryS3:
    def __init__(self, corrupt=False):
        self.corrupt = corrupt

    def put_object(self, **request):
        self.upload = request

    def get_object(self, **request):
        assert request['Bucket'] == self.upload['Bucket']
        assert request['Key'] == self.upload['Key']
        self.body = BytesIO(b'wrong bytes' if self.corrupt else self.upload['Body'])
        return {'Body': self.body}


class BackupChecks(unittest.TestCase):
    def test_verified_upload_uses_encryption_and_closes_download(self):
        client = MemoryS3()
        digest = upload_and_verify(client, 'demo-bucket', 'demo.json', b'{"reports":[]}')
        self.assertEqual(client.upload['ServerSideEncryption'], 'AES256')
        self.assertNotIn('ACL', client.upload)
        self.assertEqual(client.upload['Metadata']['sha256'], digest)
        self.assertTrue(client.body.closed)

    def test_mismatch_is_failure(self):
        client = MemoryS3(corrupt=True)
        with self.assertRaises(RuntimeError):
            upload_and_verify(client, 'demo-bucket', 'demo.json', b'{"reports":[]}')
        self.assertTrue(client.body.closed)

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'missing.sqlite3'
            with self.assertRaises(sqlite3.OperationalError):
                export_reports(database)
            self.assertFalse(database.exists())


if __name__ == '__main__':
    unittest.main()
