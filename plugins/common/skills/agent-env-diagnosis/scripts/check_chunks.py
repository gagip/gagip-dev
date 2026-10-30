#!/usr/bin/env python3
"""서브에이전트 출력이 입력 묶음과 하나씩 맞는지 대조한다. 어긋나면 종료 코드 1.

  chunks/chunk_NN.md 의 세션 키   ↔ classified/chunk_NN.json 의 id
  context/ctx_NN.jsonl 의 n      ↔ judged/judged_NN.json 의 n
"""

import argparse
import collections
import glob
import json
import os
import re
import sys


def compare(label, want, got):
    """키마다 입력과 같은 횟수만큼 출력에 있어야 한다."""
    wc, gc = collections.Counter(want), collections.Counter(got)
    missing, extra = wc - gc, gc - wc
    others = sum(v for k, v in extra.items() if k not in wc)
    bad = bool(missing or extra)
    print(f"{label}: 입력 {len(want)} 출력 {len(got)} 누락 {sum(missing.values())} 남의것 {others} 중복 {sum(extra.values()) - others}"
          + (" ← 어긋남" if bad else ""))
    return bad


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError) as e:
        return None, type(e).__name__


def check(out_dir, stage):
    pattern = ("chunks", "chunk_*.md") if stage == "classified" else ("context", "ctx_*.jsonl")
    if not glob.glob(os.path.join(out_dir, *pattern)):
        print(f"{os.path.join(out_dir, *pattern)}: 대조할 입력 묶음이 없다")
        return True
    bad = False
    if stage == "classified":
        for src in sorted(glob.glob(os.path.join(out_dir, "chunks", "chunk_*.md"))):
            n = os.path.basename(src)[6:8]
            with open(src, encoding="utf-8") as fh:
                want = re.findall(r"^### (\S+)", fh.read(), re.M)
            data, err = load_json(os.path.join(out_dir, "classified", f"chunk_{n}.json"))
            if err:
                print(f"chunk_{n}: 출력 읽기 실패 {err}")
                bad = True
                continue
            bad |= compare(f"chunk_{n}", want, [str(s.get("id")) for s in data])
    else:
        for src in sorted(glob.glob(os.path.join(out_dir, "context", "ctx_*.jsonl"))):
            n = os.path.basename(src)[4:6]
            with open(src, encoding="utf-8") as fh:
                want = [json.loads(l)["n"] for l in fh if l.strip()]
            data, err = load_json(os.path.join(out_dir, "judged", f"judged_{n}.json"))
            if err:
                print(f"judged_{n}: 출력 읽기 실패 {err}")
                bad = True
                continue
            bad |= compare(f"judged_{n}", want, [r.get("n") for r in data])
    return bad


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--stage", choices=("classified", "judged"), default="classified")
    args = p.parse_args(argv)
    sys.exit(1 if check(args.out_dir, args.stage) else 0)


if __name__ == "__main__":
    main()
