"""Un dépôt à jour ne suffit pas si Pages sert encore la version précédente."""

from io import BytesIO
from unittest.mock import Mock

import pytest

from projects.dashboard import verify_publication as vp


@pytest.mark.parametrize("remote, expected", [(b"nouveau\n", 0), (b"ancien\n", 1)])
def test_publication_requires_matching_public_files(tmp_path, monkeypatch, remote, expected):
    (tmp_path / "data.json").write_bytes(b"nouveau\r\n")
    monkeypatch.setattr(vp, "DOCS", tmp_path)
    monkeypatch.setattr(vp, "FILES", ("data.json",))
    monkeypatch.setattr(vp, "urlopen", lambda *args, **kwargs: BytesIO(remote))
    monkeypatch.setattr(vp.time, "sleep", Mock())
    assert vp.main() == expected
