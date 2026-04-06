"""P0 UUID 검증 테스트."""
import re

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class TestUUIDValidation:
    def test_valid_uuid(self):
        assert _UUID_RE.match("550e8400-e29b-41d4-a716-446655440000")

    def test_valid_uuid_uppercase(self):
        assert _UUID_RE.match("550E8400-E29B-41D4-A716-446655440000")

    def test_reject_path_traversal(self):
        assert not _UUID_RE.match("../../etc/passwd")

    def test_reject_empty(self):
        assert not _UUID_RE.match("")

    def test_reject_partial_uuid(self):
        assert not _UUID_RE.match("550e8400-e29b")

    def test_reject_dots(self):
        assert not _UUID_RE.match("../uploads/secret")

    def test_reject_slashes(self):
        assert not _UUID_RE.match("abc/def/ghi")
