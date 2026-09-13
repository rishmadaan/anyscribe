"""The standalone skill must retain its grant and complete license."""

from pathlib import Path

from anyscribe.cli import skill_cmd
from anyscribe.config.paths import get_skill_source_dir


def test_bundled_skill_license_matches_project():
    project_license = Path(__file__).resolve().parents[1] / "LICENSE"
    assert get_skill_source_dir().joinpath("LICENSE").read_text(encoding="utf-8") == (
        project_license.read_text(encoding="utf-8")
    )


def test_installed_skill_retains_license_and_utf8_references(tmp_path, monkeypatch):
    target = tmp_path / "installed-skill"
    monkeypatch.setattr(skill_cmd, "ASCLI_SKILL_TARGET", target)

    assert skill_cmd.copy_skill_files(quiet=True) == target

    source = get_skill_source_dir()
    assert (target / "LICENSE").read_text(encoding="utf-8") == source.joinpath("LICENSE").read_text(
        encoding="utf-8"
    )
    guide = (target / "SKILL.md").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Rishabh Madaan" in guide
    assert "AGPL-3.0-or-later" in guide
    for name in ("commands.md", "providers.md", "troubleshooting.md", "config.md"):
        assert (target / "references" / name).read_text(encoding="utf-8") == (
            source.joinpath("references", name).read_text(encoding="utf-8")
        )
