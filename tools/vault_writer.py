"""Obsidian保管庫にAI・アプリの出力を書き込むための小さなライブラリ（標準ライブラリのみ）。

使い方（Pythonから）:
    from vault_writer import write_output, append_ai_memo
    write_output("/path/to/AI-Vault", source="jev", title="朝の判定",
                 body="傘：必要\n重要メール：1件", project="JEV判定アプリ")
    append_ai_memo("/path/to/AI-Vault", "JEV判定アプリ", "判定精度が上がった", source="claude")

使い方（コマンドラインから）:
    python vault_writer.py VAULT_PATH out  --source jev --title 朝の判定 --body "傘：必要" --project JEV判定アプリ
    python vault_writer.py VAULT_PATH memo --source claude --project JEV判定アプリ --body "メモ"
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
OUTPUT_DIR = "20_AI-Output"
PROJECT_DIR = "10_Projects"
MEMO_HEADING = "## AIメモ"


def _safe(name: str) -> str:
    """ファイル名に使えない文字を置き換える。"""
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "-", name).strip() or "untitled"


def write_output(vault: str | Path, source: str, title: str, body: str,
                 project: str | None = None, tags: list[str] | None = None,
                 now: datetime | None = None) -> Path:
    """20_AI-Output/ に新しいノートを作り、そのパスを返す。"""
    now = now or datetime.now(JST)
    out_dir = Path(vault) / OUTPUT_DIR / now.strftime("%Y-%m")
    out_dir.mkdir(parents=True, exist_ok=True)

    base = f"{now:%Y-%m-%d_%H%M}_{_safe(source)}_{_safe(title)}"
    path = out_dir / f"{base}.md"
    n = 2
    while path.exists():  # 同じ分に複数回書いても上書きしない
        path = out_dir / f"{base}_{n}.md"
        n += 1

    all_tags = ["ai-output", _safe(source)] + (tags or [])
    lines = ["---", f"source: {source}", f"created: {now.isoformat(timespec='seconds')}"]
    if project:
        lines.append(f'project: "[[{project}]]"')
    lines.append(f"tags: [{', '.join(all_tags)}]")
    lines += ["---", f"# {title}", "", body.rstrip(), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def append_ai_memo(vault: str | Path, project: str, text: str, source: str,
                   now: datetime | None = None) -> Path:
    """10_Projects/<project>.md の「## AIメモ」セクション末尾に1行追記する。"""
    now = now or datetime.now(JST)
    path = Path(vault) / PROJECT_DIR / f"{_safe(project)}.md"
    if not path.exists():
        raise FileNotFoundError(f"プロジェクトノートがありません: {path}")

    content = path.read_text(encoding="utf-8").rstrip("\n")
    if MEMO_HEADING not in content:
        content += f"\n\n{MEMO_HEADING}"
    entry = f"- {now:%Y-%m-%d %H:%M} ({source}) {text.strip()}"

    head, _, tail = content.partition(MEMO_HEADING)
    nxt = re.search(r"\n## ", tail)  # AIメモの後ろに別の見出しがあればその手前に入れる
    if nxt:
        tail = tail[: nxt.start()].rstrip("\n") + "\n" + entry + "\n" + tail[nxt.start():]
    else:
        tail = tail.rstrip("\n") + "\n" + entry
    path.write_text(head + MEMO_HEADING + tail + "\n", encoding="utf-8")
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="Obsidian保管庫に書き込む")
    p.add_argument("vault")
    p.add_argument("mode", choices=["out", "memo"])
    p.add_argument("--source", required=True)
    p.add_argument("--title", default="出力")
    p.add_argument("--body", required=True)
    p.add_argument("--project")
    a = p.parse_args()
    if a.mode == "out":
        print(write_output(a.vault, a.source, a.title, a.body, a.project))
    else:
        if not a.project:
            p.error("memo には --project が必要です")
        print(append_ai_memo(a.vault, a.project, a.body, a.source))


if __name__ == "__main__":
    main()
