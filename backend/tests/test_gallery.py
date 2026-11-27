import json
import os
from copy import deepcopy
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.import_samples import ROLES, import_samples
from backend.app.main import create_app
from backend.app.storage import Storage, connect, media_path, migrate


class GalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.storage = Storage(self.root / "db.sqlite3", self.root / "media")
        self.source = self.root / "public"
        self.metadata = self.root / "samples.json"
        self.albums = []
        for album_id in ("second", "first"):
            photos = []
            for photo_id in (f"{album_id}-b", f"{album_id}-a"):
                photo = {"id": photo_id, "alt": f"Alt {photo_id}"}
                for role in ROLES:
                    relative = f"photos/albums/{album_id}/{photo_id}-{role}.jpg"
                    path = self.source / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"\xff\xd8fixture-" + relative.encode() + b"\xff\xd9")
                    photo[role] = {"src": f"/{relative}", "width": 240, "height": 180}
                photos.append(photo)
            self.albums.append({"id": album_id, "title": album_id.title(), "photos": photos})
        self.metadata.write_text(json.dumps(self.albums), encoding="utf-8")

    def seed(self) -> str:
        return import_samples(self.storage, self.metadata, self.source)

    def client(self, *, raise_server_exceptions: bool = True) -> TestClient:
        return TestClient(create_app(self.storage), raise_server_exceptions=raise_server_exceptions)

    def test_import_order_dimensions_and_exact_bytes(self) -> None:
        self.assertIn("12 verified", self.seed())
        with self.client() as client:
            response = client.get("/api/albums")
            self.assertEqual(response.headers["cache-control"], "no-store")
            actual = response.json()
            self.assertEqual([a["id"] for a in actual], ["second", "first"])
            for expected_album, actual_album in zip(self.albums, actual):
                self.assertEqual(expected_album["title"], actual_album["title"])
                for expected, photo in zip(expected_album["photos"], actual_album["photos"]):
                    self.assertEqual(expected["id"], photo["id"])
                    self.assertEqual(expected["alt"], photo["alt"])
                    for role in ROLES:
                        self.assertEqual((photo[role]["width"], photo[role]["height"]), (240, 180))
                        media = client.get(photo[role]["src"])
                        self.assertEqual(media.status_code, 200)
                        self.assertEqual(media.headers["content-type"], "image/jpeg")
                        self.assertEqual(media.headers["cache-control"], "no-store")
                        self.assertEqual(media.content, (self.source / expected[role]["src"].lstrip("/")).read_bytes())

    def test_repeat_import_and_restart_preserve_manual_edits(self) -> None:
        self.seed()
        with self.client() as client:
            self.assertEqual(len(client.get("/api/albums").json()), 2)
        with connect(self.storage) as db:
            db.execute("UPDATE albums SET title = 'Edited', position = 9 WHERE id = 'second'")
            db.execute("UPDATE photos SET position = 9 WHERE id = 'first-b'")
        media = self.storage.media / "albums/first/first-a-viewer.jpg"
        media.write_bytes(b"manual replacement")
        self.metadata.unlink()
        self.assertIn("unchanged", self.seed())
        migrate(self.storage)
        with self.client() as client:
            albums = client.get("/api/albums").json()
            self.assertEqual([a["title"] for a in albums], ["First", "Edited"])
            self.assertEqual(albums[0]["photos"][0]["id"], "first-a")
            self.assertEqual(client.get("/api/media/first-a/viewer").content, b"manual replacement")
        with connect(self.storage) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM variants").fetchone()[0], 12)

    def test_missing_input_leaves_no_partial_collection(self) -> None:
        (self.source / "photos/albums/first/first-a-viewer.jpg").unlink()
        with self.assertRaisesRegex(ValueError, "Missing source"):
            self.seed()
        with connect(self.storage) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM albums").fetchone()[0], 0)
        self.assertEqual(list(self.storage.media.iterdir()), [])

    def test_copy_failure_rolls_back(self) -> None:
        with patch("backend.app.import_samples.shutil.copyfile", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.seed()
        with connect(self.storage) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM albums").fetchone()[0], 0)
        self.assertEqual(list(self.storage.media.iterdir()), [])

    def test_invalid_metadata_and_destination_conflicts(self) -> None:
        self.albums[0]["photos"][0]["preview"]["src"] = "/../secret.jpg"
        self.metadata.write_text(json.dumps(self.albums))
        with self.assertRaisesRegex(ValueError, "Unexpected source"):
            self.seed()
        self.albums[0]["photos"][0]["preview"]["src"] = "/photos/albums/second/second-b-preview.jpg"
        self.metadata.write_text(json.dumps(self.albums))
        (self.storage.media / "albums").mkdir()
        with self.assertRaisesRegex(ValueError, "Destination already exists"):
            self.seed()

    def test_drafts_unpublish_missing_private_and_traversal(self) -> None:
        self.seed()
        with self.client() as client:
            self.assertEqual(client.get("/api/media/second-b/viewer").status_code, 200)
            with connect(self.storage) as db:
                db.execute("UPDATE albums SET published = 0 WHERE id = 'second'")
            self.assertEqual([a["id"] for a in client.get("/api/albums").json()], ["first"])
            self.assertEqual(client.get("/api/media/second-b/viewer").status_code, 404)
            (self.storage.media / "unrelated.jpg").write_bytes(b"private")
            for url in ("/api/media/unrelated.jpg", "/api/media/unknown/viewer", "/api/media/../db.sqlite3", "/api/media/%2e%2e%2fdb.sqlite3/viewer", "/api/media/first-a/original", "/storage/db.sqlite3"):
                self.assertIn(client.get(url).status_code, (404, 422))
            for relative in ("../secret.jpg", str(self.metadata), "C:\\secret.jpg", "albums/../../secret.jpg", "file:secret.jpg"):
                with connect(self.storage) as db:
                    db.execute("UPDATE variants SET path = ? WHERE photo_id = 'first-a' AND role = 'viewer'", (relative,))
                self.assertEqual(client.get("/api/media/first-a/viewer").status_code, 404)
            (self.storage.media / "albums/first/first-b-viewer.jpg").unlink()
            self.assertEqual(client.get("/api/media/first-b/viewer").status_code, 404)

    def test_empty_read_only_and_backend_failure(self) -> None:
        with self.client(raise_server_exceptions=False) as client:
            self.assertEqual(client.get("/api/health").json(), {"status": "ok"})
            self.assertEqual(client.get("/api/albums").json(), [])
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                for url in ("/api/albums", "/api/media/photo/viewer"):
                    self.assertEqual(client.request(method, url).status_code, 405)
            with connect(self.storage) as db:
                db.execute("DROP TABLE variants")
                db.execute("INSERT INTO albums VALUES ('album', 'Album', 0, 1)")
                db.execute("INSERT INTO photos VALUES ('photo', 'album', 'Alt', 0)")
            self.assertEqual(client.get("/api/albums").status_code, 500)

    def test_path_resolution_rejects_symlink_escape(self) -> None:
        migrate(self.storage)
        link = self.storage.media / "outside"
        try:
            link.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest("OS does not permit symlink creation")
        with self.assertRaises(ValueError):
            media_path(self.storage.media, "outside/private.jpg")

    def test_constraints_and_incomplete_metadata_failure(self) -> None:
        self.seed()
        with connect(self.storage) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO photos VALUES ('orphan', 'absent', '', 0)")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE variants SET width = 0")
            db.execute("DELETE FROM variants WHERE photo_id = 'first-a' AND role = 'viewer'")
        with self.client() as client:
            self.assertEqual(client.get("/api/albums").status_code, 500)

    def test_future_schema_is_rejected(self) -> None:
        migrate(self.storage)
        with connect(self.storage) as db:
            db.execute("PRAGMA user_version = 99")
        with self.assertRaisesRegex(RuntimeError, "newer"):
            migrate(self.storage)

    def test_invalid_json_fields_fail_before_import(self) -> None:
        cases = [
            ((0, "id"), 123),
            ((0, "id"), "invalid/id"),
            ((0, "title"), 123),
            ((0, "title"), "  "),
            ((0, "photos"), {}),
            ((0, "photos", 0, "id"), None),
            ((0, "photos", 0, "alt"), False),
            ((0, "photos", 0, "preview", "src"), 123),
            ((0, "photos", 0, "preview", "width"), "240"),
            ((0, "photos", 0, "preview", "width"), 240.0),
            ((0, "photos", 0, "preview", "width"), True),
            ((0, "photos", 0, "preview", "height"), 0),
            ((0, "photos", 0, "viewer"), None),
        ]
        for location, value in cases:
            with self.subTest(location=location, value=value):
                data = deepcopy(self.albums)
                target = data
                for key in location[:-1]:
                    target = target[key]
                target[location[-1]] = value
                self.metadata.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValidationError) as error:
                    self.seed()
                self.assertEqual(error.exception.errors()[0]["loc"], location)
                with connect(self.storage) as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM albums").fetchone()[0], 0)
                self.assertEqual(list(self.storage.media.iterdir()), [])

    def test_invalid_collection_and_missing_field(self) -> None:
        missing_field = deepcopy(self.albums)
        del missing_field[0]["photos"][0]["alt"]
        for data in ({}, [], None, missing_field):
            with self.subTest(data=data):
                self.metadata.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValidationError):
                    self.seed()

    def test_duplicate_ids_remain_rejected(self) -> None:
        self.albums.append(deepcopy(self.albums[0]))
        self.metadata.write_text(json.dumps(self.albums), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate ID"):
            self.seed()

    @unittest.skipUnless(os.name == "nt", "Windows ACL regression")
    def test_imported_media_inherits_storage_permissions(self) -> None:
        self.seed()
        environment = os.environ.copy()
        environment["GALLERY_TEST_ALBUMS"] = str(self.storage.media / "albums")
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "$ErrorActionPreference = 'Stop'; "
             "$acl = Get-Acl -LiteralPath $env:GALLERY_TEST_ALBUMS; "
             "if ($acl.AreAccessRulesProtected -or "
             "@($acl.Access | Where-Object { -not $_.IsInherited }).Count -gt 0) { exit 1 }"],
            env=environment, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
