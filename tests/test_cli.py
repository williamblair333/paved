import pytest

from paved import cli


def test_parser_requires_subcommand():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_repair_args_parse():
    a = cli.build_parser().parse_args(
        ["repair", "/data/x.mp4", "--dry-run", "--recursive", "--out", "/o"]
    )
    assert a.command == "repair"
    assert a.path == "/data/x.mp4"
    assert a.dry_run is True
    assert a.recursive is True
    assert a.out == "/o"


def test_transcribe_llm_choices():
    a = cli.build_parser().parse_args(
        ["transcribe", "/data/x.mp4", "--engine", "vosk", "--llm", "summary"]
    )
    assert a.engine == "vosk"
    assert a.llm == "summary"
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["transcribe", "/x", "--llm", "bogus"])


def test_engines_command_runs(capsys, monkeypatch):
    # Force a known availability so output is deterministic.
    for e in __import__("paved.transcribe", fromlist=["ALL_ENGINES"]).ALL_ENGINES:
        monkeypatch.setattr(e, "is_available", lambda: True)
    rc = cli.main(["engines"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "faster-whisper" in out
    assert "Default selection" in out
