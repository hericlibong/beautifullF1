"""Tests de sync_to_docs : garant du refresh automatique (web/ -> docs/).

Vérifie que la copie est récursive et additive — notamment que les futurs
modules ES6 (assets/modules/*.js) seront bien propagés vers docs/.
"""

from __future__ import annotations

from pathlib import Path

from projects.dashboard import sync_to_docs as sync


def _make_tree(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_sync_copies_nested_modules(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "web"
    dst = tmp_path / "docs"
    _make_tree(
        src,
        {
            "index.html": "<html>",
            "assets/dashboard.js": "// orchestrateur",
            "assets/modules/i18n.js": "export const t = () => {};",
            "assets/modules/render/duel.js": "export function renderDuelPanel(){}",
            "data/dashboard_2026.json": "{}",
        },
    )
    monkeypatch.setattr(sync, "SRC", src)
    monkeypatch.setattr(sync, "DST", dst)

    assert sync.main() == 0

    # Tous les fichiers, y compris les modules imbriqués, sont présents dans docs/
    for rel in (
        "index.html",
        "assets/dashboard.js",
        "assets/modules/i18n.js",
        "assets/modules/render/duel.js",
        "data/dashboard_2026.json",
    ):
        assert (dst / rel).is_file(), f"manquant dans docs/: {rel}"
    assert (dst / "assets/modules/render/duel.js").read_text(encoding="utf-8") == (
        "export function renderDuelPanel(){}"
    )


def test_sync_is_additive_preserves_existing_docs(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "web"
    dst = tmp_path / "docs"
    _make_tree(src, {"index.html": "<new>"})
    # Une autre viz déjà publiée dans docs/ ne doit pas être supprimée
    _make_tree(dst, {"season_summary_heatmap/index.html": "<heatmap>"})
    monkeypatch.setattr(sync, "SRC", src)
    monkeypatch.setattr(sync, "DST", dst)

    assert sync.main() == 0
    assert (dst / "season_summary_heatmap/index.html").is_file()
    assert (dst / "index.html").read_text(encoding="utf-8") == "<new>"


def test_sync_missing_source_returns_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sync, "SRC", tmp_path / "does_not_exist")
    monkeypatch.setattr(sync, "DST", tmp_path / "docs")
    assert sync.main() == 1
