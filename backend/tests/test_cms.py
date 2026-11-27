import io
import os
import sqlite3
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import cms
from backend.app.main import create_app
from backend.app.storage import Storage, connect


def jpeg(color="red", size=(64, 32), orientation=None):
    output = io.BytesIO()
    image = Image.new("RGB", size, color)
    exif = Image.Exif()
    if orientation:
        exif[274] = orientation
        exif[270] = "Private source description"
    image.save(output, "JPEG", exif=exif)
    return output.getvalue()


class CmsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = Storage(Path(self.temp.name) / "gallery.sqlite3", Path(self.temp.name) / "media")
        self.client = self.enterContext(TestClient(create_app(self.storage)))

    def create(self, photos=None, title="New album", request_id=None):
        return self.client.post("/api/admin/albums", data={"title": title, "request_id": request_id or str(uuid4())},
                                files=[("photos", ("../../untrusted.jpg", data, "image/jpeg")) for data in (photos if photos is not None else [jpeg()])])

    def albums(self):
        return self.client.get("/api/albums").json()

    def test_create_sequence_variants_orientation_and_metadata(self):
        self.assertEqual(self.create([jpeg("blue", (2000, 1000), 6), jpeg("red"), jpeg("green")]).status_code, 200)
        album = self.albums()[0]
        self.assertEqual(len(album["photos"]), 3)
        for i, photo in enumerate(album["photos"]):
            self.assertEqual(photo["alt"], f"New album — photo {i + 1}")
            for role, limit in cms.ROLES.items():
                image = Image.open(io.BytesIO(self.client.get(photo[role]["src"]).content))
                self.assertFalse(image.getexif())
                self.assertEqual(image.size, (photo[role]["width"], photo[role]["height"]))
                self.assertLessEqual(max(image.size), limit)
                if i == 0:
                    self.assertLess(image.width, image.height)
                    self.assertGreater(image.getpixel((0, 0))[2], 240)
                else:
                    self.assertEqual(image.size, (64, 32))
        self.assertEqual(len(list(self.storage.media.rglob("*.jpg"))), 9)

    def test_idempotency_persists_and_deleted_receipt_cannot_recreate(self):
        key = str(uuid4())
        first = self.create(request_id=key).json()
        with TestClient(create_app(self.storage)) as restarted:
            old = self.client
            self.client = restarted
            try:
                self.assertEqual(self.create(request_id=key).json(), first)
                self.assertEqual(self.create(title="Different", request_id=key).status_code, 409)
            finally:
                self.client = old
        self.assertEqual(len(self.albums()), 1)
        self.client.delete(f'/api/admin/albums/{first["id"]}')
        self.assertEqual(self.create(request_id=key).status_code, 409)
        self.assertEqual(self.albums(), [])

    def test_invalid_title_count_content_and_limits_leave_no_album(self):
        for title in (" ", "x" * 121):
            self.assertEqual(self.create(title=title).status_code, 422)
        for photos in ([], [b""], [b"not a jpeg"], [jpeg()[:100]], [jpeg(), b"bad"]):
            self.assertEqual(self.create(photos).status_code, 422)
        png = io.BytesIO()
        Image.new("RGB", (5, 5)).save(png, "PNG")
        self.assertEqual(self.create([png.getvalue()]).status_code, 422)
        self.assertEqual(self.create([jpeg()] * 31).status_code, 400)
        with patch.object(cms, "MAX_FILE_BYTES", 10):
            self.assertEqual(self.create().status_code, 413)
        with patch.object(cms, "MAX_TOTAL_BYTES", len(jpeg()) + 10):
            self.assertEqual(self.create([jpeg(), jpeg()]).status_code, 413)
        with patch.object(cms, "MAX_PIXELS", 10):
            self.assertEqual(self.create().status_code, 422)
        with patch.object(cms, "MAX_REQUEST_BYTES", 10):
            self.assertEqual(self.create().status_code, 413)
        self.assertEqual(self.albums(), [])
        self.assertEqual(list(self.storage.media.rglob("*.jpg")), [])

    def test_processing_rename_and_transaction_failures_roll_back(self):
        content = jpeg()
        for target, failure in (("backend.app.cms.Image.Image.save", OSError("full")),
                                ("backend.app.cms.Path.rename", OSError("rename failed"))):
            with patch(target, side_effect=failure):
                self.assertIn(self.create([content]).status_code, (422, 503))
            self.assertEqual(self.albums(), [])
            self.assertEqual(list(self.storage.media.rglob("*.jpg")), [])
        with connect(self.storage) as db:
            db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON creations BEGIN SELECT RAISE(ABORT, 'failure'); END")
        self.assertEqual(self.create().status_code, 503)
        self.assertEqual(self.albums(), [])
        self.assertEqual(list(self.storage.media.rglob("*.jpg")), [])

    def test_commit_failure_after_rename_removes_prepared_files(self):
        @contextmanager
        def fail_commit(storage):
            with connect(storage) as db:
                yield db
                raise sqlite3.OperationalError("Simulated failed commit")

        with patch.object(cms, "connect", fail_commit), self.assertLogs(cms.logger, level="ERROR"):
            self.assertEqual(self.create().status_code, 503)
        self.assertEqual(self.albums(), [])
        self.assertEqual(list(self.storage.media.rglob("*.jpg")), [])
        with connect(self.storage) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM creations").fetchone()[0], 0)

    def test_concurrent_duplicate_creation(self):
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: self.create(request_id=key), range(2)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(len(self.albums()), 1)
        self.assertEqual(len(list(self.storage.media.rglob("*.jpg"))), 3)

    def test_chunked_body_limit_without_content_length(self):
        boundary = "cms-boundary"
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="photos"; filename="image.jpg"\r\n'
                'Content-Type: image/jpeg\r\n\r\n').encode() + jpeg() + f'\r\n--{boundary}--\r\n'.encode()
        with patch.object(cms, "MAX_REQUEST_BYTES", 200):
            response = self.client.post("/api/admin/albums", content=(body[i:i + 100] for i in range(0, len(body), 100)),
                                        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.albums(), [])

    def test_order_validation_stale_order_and_restart(self):
        ids = [self.create(title=title).json()["id"] for title in ("First", "Second", "Third")]
        for invalid in ([ids[0], ids[0], ids[2]], ids[:2], ["unknown", *ids[1:]]):
            self.assertEqual(self.client.put("/api/admin/albums/order", json={"ids": invalid, "previous": ids}).status_code, 409)
            self.assertEqual([a["id"] for a in self.albums()], ids)
        new = ids[::-1]
        for _ in range(2):
            self.assertEqual(self.client.put("/api/admin/albums/order", json={"ids": new, "previous": ids}).status_code, 200)
        self.assertEqual(self.client.put("/api/admin/albums/order", json={"ids": [ids[1], ids[0], ids[2]], "previous": ids}).status_code, 409)
        with TestClient(create_app(self.storage)) as restarted:
            self.assertEqual([a["id"] for a in restarted.get("/api/albums").json()], new)

    def test_delete_isolation_revocation_and_cleanup_retry(self):
        self.create(title="Delete me")
        self.create(title="Keep me")
        deleted, retained = self.albums()
        retained_bytes = {p: p.read_bytes() for p in self.storage.media.rglob("*.jpg") if retained["id"] in str(p)}
        url = deleted["photos"][0]["viewer"]["src"]
        with patch.object(Path, "unlink", side_effect=PermissionError("locked")):
            result = self.client.delete(f'/api/admin/albums/{deleted["id"]}').json()
        self.assertEqual(result["cleanup_pending"], 3)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.albums(), [retained])
        with TestClient(create_app(self.storage)) as restarted:
            self.assertEqual(restarted.delete(f'/api/admin/albums/{deleted["id"]}').json()["cleanup_pending"], 0)
            self.assertEqual(restarted.delete(f'/api/admin/albums/{deleted["id"]}').status_code, 200)
        self.assertTrue(all(p.read_bytes() == data for p, data in retained_bytes.items()))
        self.assertEqual(len(list(self.storage.media.rglob("*.jpg"))), 3)
        with connect(self.storage) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM media_cleanup").fetchone()[0], 0)

    def test_staging_unpublished_unsafe_cleanup_and_edit_routes(self):
        self.create()
        album = self.albums()[0]
        with connect(self.storage) as db:
            db.execute("UPDATE albums SET published = 0")
        self.assertEqual(self.albums(), [])
        self.assertEqual(self.client.get(album["photos"][0]["viewer"]["src"]).status_code, 404)
        self.assertEqual(self.client.delete(f'/api/admin/albums/{album["id"]}').status_code, 404)
        for method in ("PATCH", "PUT"):
            self.assertEqual(self.client.request(method, f'/api/admin/albums/{album["id"]}').status_code, 405)
        (self.storage.media / "staging-private.jpg").write_bytes(jpeg())
        self.assertEqual(self.client.get("/api/media/staging-private.jpg/viewer").status_code, 404)
        with connect(self.storage) as db:
            db.execute("UPDATE albums SET published = 1")
            db.execute("UPDATE variants SET path = '../gallery.sqlite3' WHERE role = 'viewer'")
        self.assertEqual(self.client.delete(f'/api/admin/albums/{album["id"]}').json()["cleanup_pending"], 1)
        self.assertTrue(self.storage.database.is_file())

    @unittest.skipUnless(os.name == "nt", "Windows ACL regression")
    def test_uploaded_files_inherit_permissions(self):
        self.create()
        environment = os.environ.copy()
        environment["CMS_TEST_MEDIA"] = str(self.storage.media)
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                 "Get-ChildItem -LiteralPath $env:CMS_TEST_MEDIA -Recurse | ForEach-Object { "
                                 "$acl = Get-Acl -LiteralPath $_.FullName; "
                                 "if ($acl.AreAccessRulesProtected -or @($acl.Access | Where-Object { -not $_.IsInherited }).Count -gt 0) { exit 1 } }"],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
