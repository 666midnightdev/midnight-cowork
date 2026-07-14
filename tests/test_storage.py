import json
import os
import tempfile

from app.storage import _safe_read, _safe_write


def test_safe_read_nonexistent() -> None:
    result = _safe_read("/nonexistent/path.json", default=[])
    assert result == []


def test_safe_write_and_read() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.json")
        data = {"key": "value", "number": 42}
        _safe_write(filepath, data)
        result = _safe_read(filepath)
        assert result == data


def test_safe_read_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "bad.json")
        with open(filepath, "w") as f:
            f.write("not valid json {{{")
        result = _safe_read(filepath, default=[])
        assert result == []


def test_safe_write_atomic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "atomic.json")
        _safe_write(filepath, {"a": 1})
        _safe_write(filepath, {"a": 2})
        result = _safe_read(filepath)
        assert result == {"a": 2}
        tmp_files = [f for f in os.listdir(tmpdir) if f.endswith(".tmp")]
        assert len(tmp_files) == 0


def test_safe_read_nested_data() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "nested.json")
        data = {"chats": [{"id": "1", "messages": [{"role": "user", "content": "hi"}]}]}
        _safe_write(filepath, data)
        result = _safe_read(filepath)
        assert result == data
