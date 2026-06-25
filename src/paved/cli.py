"""PAVED command-line interface.

Subcommands:
  probe       diagnose container structure
  repair      diagnose + salvage broken video (file or folder)
  transcribe  speech-to-text with a chosen/auto engine + optional LLM post-step
  engines     list transcription engines and availability
"""
from __future__ import annotations

import argparse
import os
import sys

from paved import __version__, report


def _print(s: str = "") -> None:
    print(s, flush=True)


def cmd_probe(args) -> int:
    from paved import probe as probe_mod

    diag = probe_mod.probe(args.path)
    if args.json:
        _print(report.dumps(diag))
    else:
        _print(f"file:      {diag.path}")
        _print(f"boxes:     {', '.join(diag.boxes)}")
        _print(f"fault:     {diag.fault}")
        _print(f"detail:    {diag.detail}")
    return 0 if diag.fault == "none" else 2


def cmd_repair(args) -> int:
    from paved import repair as repair_mod

    targets = list(repair_mod.iter_videos(args.path, recursive=args.recursive))
    if not targets:
        _print(f"No video files found at: {args.path}")
        return 2
    results, failures = [], 0
    for src in targets:
        res = repair_mod.repair_file(src, out_dir=args.out, dry_run=args.dry_run)
        results.append(res)
        if not args.json:
            _print(f"\n=== {src} ===")
            _print(res.human())
        if not res.success and not args.dry_run:
            failures += 1
    if args.json:
        _print(report.dumps([r.to_dict() for r in results]))
    if not args.dry_run:
        ok = sum(1 for r in results if r.success)
        _print(f"\nRepaired {ok}/{len(results)} file(s).")
    # Non-zero exit if any real repair failed (observability for scripts).
    return 1 if failures else 0


def cmd_transcribe(args) -> int:
    from paved import transcribe as tr
    from paved.llm import process as llm_process

    targets = _iter_media(args.path, args.recursive)
    if not targets:
        _print(f"No media files found at: {args.path}")
        return 2
    rc = 0
    for src in targets:
        try:
            t = tr.transcribe_file(src, engine_name=args.engine, model=args.model)
        except Exception as e:
            _print(f"ERROR transcribing {src}: {e}", )
            rc = 1
            continue
        text = t.text
        llm_warn = ""
        if args.llm != "off":
            r = llm_process(
                text,
                mode=args.llm,
                provider=args.llm_provider,
                model=args.llm_model,
            )
            text = r.text
            if not r.ok:
                llm_warn = r.warning

        out_dir = args.out or os.path.dirname(os.path.abspath(src)) or "."
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(src))[0]
        txt_path = os.path.join(out_dir, f"{stem}.txt")
        json_path = os.path.join(out_dir, f"{stem}.json")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(report.dumps(t.to_dict()))

        _print(f"\n=== {src} ===")
        _print(f"engine:  {t.engine} (model {t.model})")
        _print(f"text:    {txt_path}")
        _print(f"json:    {json_path}")
        if llm_warn:
            _print(f"WARNING: {llm_warn}")
    return rc


def cmd_engines(args) -> int:
    from paved import transcribe as tr

    _print("Transcription engines (default = first available, by priority):\n")
    for e in sorted(tr.ALL_ENGINES, key=lambda x: x.priority):
        status = "available" if e.is_available() else "not installed"
        _print(f"  {e.name:16} priority={e.priority:<3} {status}  (model: {e.default_model})")
    avail = tr.available_engines()
    _print(f"\nDefault selection: {avail[0].name if avail else '(none available)'}")
    return 0


def _iter_media(path: str, recursive: bool):
    from paved.repair import iter_videos

    exts = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
    if os.path.isfile(path):
        return [path]
    media = list(iter_videos(path, recursive=recursive))
    walker = os.walk(path) if recursive else [(path, [], os.listdir(path))]
    for root, _d, files in walker:
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in exts:
                media.append(os.path.join(root, name))
    return sorted(set(media))


def build_parser() -> argparse.ArgumentParser:
    from paved.llm import PROVIDER_NAMES
    p = argparse.ArgumentParser(
        prog="paved",
        description="PAVED — repair broken videos and transcribe speech (offline).",
    )
    p.add_argument("--version", action="version", version=f"paved {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pp = sub.add_parser("probe", help="diagnose container structure")
    pp.add_argument("path")
    pp.add_argument("--json", action="store_true")
    pp.set_defaults(func=cmd_probe)

    pr = sub.add_parser("repair", help="repair/salvage broken video(s)")
    pr.add_argument("path", help="file or directory")
    pr.add_argument("--out", help="output directory (default: alongside source)")
    pr.add_argument("--dry-run", action="store_true", help="diagnose only, write nothing")
    pr.add_argument("--recursive", action="store_true", help="recurse into subdirectories")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_repair)

    pt = sub.add_parser("transcribe", help="speech-to-text")
    pt.add_argument("path", help="file or directory")
    pt.add_argument("--engine", help="engine name (default: best available)")
    pt.add_argument("--model", help="engine model (default: engine's default)")
    pt.add_argument("--llm", choices=["off", "clean", "summary"], default="off",
                    help="optional local-LLM post-step (default: off)")
    pt.add_argument("--llm-provider", dest="llm_provider",
                    choices=PROVIDER_NAMES, default=None,
                    help="LLM provider (default: PAVED_LLM_PROVIDER env var, or 'ollama')")
    pt.add_argument("--llm-model", dest="llm_model", default=None,
                    help="model override for chosen LLM provider")
    pt.add_argument("--out", help="output directory (default: alongside source)")
    pt.add_argument("--recursive", action="store_true")
    pt.set_defaults(func=cmd_transcribe)

    pe = sub.add_parser("engines", help="list transcription engines")
    pe.set_defaults(func=cmd_engines)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # surface the error and fail loudly — no silent success
        _print(f"paved: error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
