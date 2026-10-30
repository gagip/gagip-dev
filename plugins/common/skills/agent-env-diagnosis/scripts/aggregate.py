#!/usr/bin/env python3
"""2단계 집계 + 3단계 개선 후보.

입력(--out-dir 아래):
  sessions.jsonl, extract_meta.json, context_meta.json   extract.py 산출
  classified/chunk_*.json                                1차 분류 (업무 종류·단계·교정 후보)
  context/ctx_*.jsonl, judged/judged_*.json              교정 재판정 (진짜 여부·종류·원인·규칙 자리)
  env.json                                               env_scan.py --json (있으면)
  review.json                                            독립 검토 결과 (있으면)
출력:
  report_data.json   render_html.py 입력
  baseline.json      다음 진단 때 --baseline 으로 넘길 기준값
"""

import argparse
import collections
import glob
import json
import os
import re
import statistics

STAGES = ["요청", "의도확인", "맥락수집", "조사", "계획서", "계획검토", "시안", "사용자결정", "구현", "자체검증",
          "독립리뷰", "문서작성", "시각보고", "커밋", "PR", "머지", "게시", "회고", "메모리저장"]
CAUSES = ["규칙있음_어김", "판단오류", "규칙없음", "스킬미호출", "도구한계"]
EXCLUDED_AUTOMATION = "평가"
MIN_STAGE_SHARE = 0.15
MIN_CELL = 3
MIN_REPEAT = 2
RARE_DETAIL_SESSIONS = 2
MAX_PER_SOURCE = 10


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def stage_name(s):
    return str(s or "?").split("(")[0].strip()


def file_key(path):
    parts = str(path or "").rstrip("/").split("/")
    return "/".join(parts[-3:])


def was_opened(rule_file, opened):
    """상대 경로(memory/x.md)로 연 것도 잡되, 세 마디가 다 있으면 세 마디로 맞춘다."""
    want = str(rule_file or "").rstrip("/").split("/")
    for p in opened:
        got = str(p).rstrip("/").split("/")
        n = min(3, len(got), len(want))
        if n >= 2 and got[-n:] == want[-n:]:
            return True
    return False


def skill_name(path_or_name):
    m = re.search(r"skills/([^/]+)/", path_or_name or "")
    return (m.group(1) if m else str(path_or_name or "")).split(":")[-1]


def rule_loaded(j, ctx, opened):
    """그 교정 시점에 막을 규칙이 에이전트 앞에 있었나. True/False/None(판단 불가).
    opened: 그 교정 전에 도구로 언급한 .md 경로 전부."""
    place, f = j.get("rule_place"), j.get("rule_file") or ""
    if place == "상시지침":
        return True
    if place in ("상세파일", "메모리"):
        if not f:
            return None
        return was_opened(f, opened)
    if place == "스킬":
        name = skill_name(f)
        if not name:
            return None
        return any(name == skill_name(s) for s in ctx.get("skills_so_far") or []) or was_opened(f, opened)
    return None


def load(out_dir):
    meta = {r["key"]: r for r in read_jsonl(os.path.join(out_dir, "sessions.jsonl"))}
    rows, evals, unknown, seen = [], 0, 0, set()
    for f in sorted(glob.glob(os.path.join(out_dir, "classified", "chunk_*.json"))):
        for s in read_json(f, []):
            m = meta.get(str(s.get("id")))
            if m is None:
                unknown += 1
                continue
            if s["id"] in seen:
                continue
            seen.add(s["id"])
            if EXCLUDED_AUTOMATION in str(s.get("automated") or ""):
                evals += 1
                continue
            s["_meta"] = m
            rows.append(s)
    ctx = {}
    for f in sorted(glob.glob(os.path.join(out_dir, "context", "ctx_*.jsonl"))):
        for r in read_jsonl(f):
            ctx[r["n"]] = r
    opened = {int(k): v for k, v in (read_json(os.path.join(out_dir, "context", "opened.json"), {}) or {}).items()}
    judged = []
    for f in sorted(glob.glob(os.path.join(out_dir, "judged", "judged_*.json"))):
        for j in read_json(f, []):
            c = ctx.get(j.get("n"))
            if c is not None:
                judged.append((j, c, opened.get(j.get("n"), c.get("md_opened_before") or [])))
    return meta, rows, evals, unknown, judged


def build(out_dir, baseline=None):
    meta, rows, evals, unknown, judged = load(out_dir)
    env = read_json(os.path.join(out_dir, "env.json"))
    keep = {r["_meta"]["key"]: r for r in rows}
    corr = []
    for j, c, op in judged:
        r = keep.get(c["session"])
        if r is None or not j.get("real"):
            continue
        corr.append(dict(
            work_type=r.get("work_type") or "기타", session=c["session"], date=c["date"], title=c.get("title"),
            quote=c.get("quote"), stage=stage_name(j.get("stage") or c.get("stage")), kind=j.get("kind") or "기타",
            cause=j.get("cause") or "판단오류", rule_place=j.get("rule_place") or "없음", rule_file=j.get("rule_file") or "",
            rule_text=j.get("rule_text") or "", missing_skill=j.get("missing_skill") or "", what=j.get("what") or "",
            loaded=rule_loaded(j, c, op),
        ))
    months = sorted({r["_meta"]["start"][:7] for r in rows})
    by_type = collections.defaultdict(list)
    for r in rows:
        by_type[r.get("work_type") or "기타"].append(r)

    types = {}
    for wt, rs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        n = len(rs)
        cs = [c for c in corr if c["work_type"] == wt]
        stage_c, seqs, skills = collections.Counter(), collections.Counter(), collections.Counter()
        for r in rs:
            st = [stage_name(s) for s in r.get("stages") or []]
            st = [s for i, s in enumerate(st) if i == 0 or st[i - 1] != s]
            stage_c.update(set(st))
            seqs[" → ".join(st[:8])] += 1
            skills.update(r["_meta"]["skills"].keys())
            skills.update("agent:" + a for a in r["_meta"].get("agents", {}))
        stages = []
        for st in STAGES + sorted((set(stage_c) | {c["stage"] for c in cs}) - set(STAGES)):
            share = round(stage_c[st] / n, 2)
            sc = [c for c in cs if c["stage"] == st]
            if share < MIN_STAGE_SHARE and not sc:
                continue
            stages.append(dict(name=st, share=share, corrections=len(sc),
                               kinds=collections.Counter(c["kind"] for c in sc).most_common(3),
                               quotes=[dict(q=c["quote"], what=c["what"], kind=c["kind"], cause=c["cause"], date=c["date"]) for c in sc[:4]]))
        types[wt] = dict(
            sessions=n, by_tool=dict(collections.Counter(r["_meta"]["tool"] for r in rs)),
            scheduled=sum(1 for r in rs if "예약" in str(r.get("automated") or "")),
            forks=sum(1 for r in rs if r["_meta"].get("fork_of")),
            median_user_msgs=statistics.median([r["_meta"]["user_msgs"] for r in rs]),
            corrections=len(cs), sessions_with_corrections=len({c["session"] for c in cs}),
            stages=stages, top_sequences=seqs.most_common(3), top_skills=skills.most_common(8),
            kinds=collections.Counter(c["kind"] for c in cs).most_common(5),
            causes=collections.Counter(c["cause"] for c in cs).most_common(),
        )

    kinds = [k for k, _ in collections.Counter(c["kind"] for c in corr).most_common(10)]
    stage_rows = []
    for st in STAGES + sorted({c["stage"] for c in corr} - set(STAGES)):
        v = [sum(1 for c in corr if c["stage"] == st and c["kind"] == k) for k in kinds]
        if any(v):
            stage_rows.append([st, v])

    place_loaded = collections.Counter((c["rule_place"], c["loaded"]) for c in corr if c["cause"] == "규칙있음_어김")
    rules = collections.defaultdict(list)
    for c in corr:
        if c["cause"] == "규칙있음_어김":
            # 규칙 요지 문장은 판정마다 표현이 달라 묶음 기준으로 못 쓴다. 파일 안에서는 잘못의 종류로 나눈다.
            rules[(c["rule_place"], c["rule_file"], c["kind"])].append(c)
    violated = sorted(([dict(place=p, file=f, kind=k, count=len(cs), loaded=sum(1 for c in cs if c["loaded"]),
                             not_loaded=sum(1 for c in cs if c["loaded"] is False),
                             rule_text=collections.Counter(c["rule_text"] for c in cs).most_common(1)[0][0],
                             examples=[dict(q=c["quote"], what=c["what"], date=c["date"]) for c in cs[:3]])
                        for (p, f, k), cs in rules.items()]), key=lambda r: -r["count"])
    no_rule = collections.defaultdict(list)
    for c in corr:
        if c["cause"] == "규칙없음":
            no_rule[c["kind"]].append(c)
    missing = collections.Counter(c["missing_skill"] for c in corr if c["cause"] == "스킬미호출" and c["missing_skill"])

    cells = collections.Counter((c["work_type"], c["stage"], c["kind"]) for c in corr)
    cand = []
    for (wt, st, k), v in cells.most_common(MAX_PER_SOURCE):
        if v >= MIN_CELL:
            cand.append(dict(source="교정이 몰린 칸", item=f"{wt} · {st} · {k}", count=v,
                             action="그 단계를 맡는 스킬 본문이나 지침 문장을 고친다", handoff="retrospective"))
    for r in violated[:MAX_PER_SOURCE]:
        if r["count"] < MIN_REPEAT:
            continue
        if r["not_loaded"] > r["loaded"]:
            action = "자리를 옮긴다(상세 파일·메모리 → 그 단계 스킬 본문이나 상시 지침)"
        elif r["loaded"]:
            action = "읽혔는데도 어겼다: 훅·검사 스크립트로 바꾼다"
        else:
            action = "읽혔는지 판단할 수 없다: 근거 교정을 열어 보고 정한다"
        cand.append(dict(source="규칙이 있었는데 어김", item=f"{r['place']} {r['file'] or ''} · {r['kind']} — 예: {r['rule_text']}".strip(),
                         count=r["count"], action=action, handoff="retrospective"))
    for k, cs in sorted(no_rule.items(), key=lambda kv: -len(kv[1]))[:MAX_PER_SOURCE]:
        if len(cs) >= MIN_REPEAT:
            cand.append(dict(source="규칙이 없던 반복 실수", item=f"{k}: " + " / ".join(c["what"] for c in cs[:3]), count=len(cs),
                             action="새 규칙 초안(지침·메모리) 또는 새 스킬", handoff="retrospective / build-skill"))
    for sk, v in missing.most_common(MAX_PER_SOURCE):
        if v >= MIN_REPEAT:
            cand.append(dict(source="스킬 안 부름", item=sk, count=v,
                             action="스킬 설명(켜지는 말)이나 앞 단계 스킬의 다음 단계 안내를 고친다", handoff="retrospective"))
    env_sum = None
    if env:
        never = [m for m in env.get("memory") or [] if not m["opened_sessions"]]
        rare = [d for d in env.get("details") or [] if d["opened_sessions"] <= RARE_DETAIL_SESSIONS]
        env_sum = dict(
            sessions=env.get("sessions"), always=env.get("always") or [],
            always_bytes=sum(a["bytes"] for a in env.get("always") or []),
            details=sorted(env.get("details") or [], key=lambda d: -d["opened_sessions"]),
            memory_files=len(env.get("memory") or []), memory_never=len(never),
            memory_never_files=[os.path.basename(m["file"]) for m in never][:40],
            hooks_configured=env.get("hooks_configured") or [], hooks_fired=(env.get("hooks_fired") or [])[:10],
        )
        for d in rare:
            cand.append(dict(source="안 읽히는 상세 파일", item=file_key(d["file"]), count=d["opened_sessions"],
                             action="읽기를 그 일을 맡는 스킬 첫 단계로 옮기거나, 필요한 줄을 스킬 본문으로 가져온다", handoff="retrospective"))
        if never:
            cand.append(dict(source="안 열리는 메모리", item=f"{len(never)}/{len(env.get('memory'))}개 파일", count=len(never),
                             action="보관·병합 후보를 고른다", handoff="consolidate-memory"))
        cand.append(dict(source="상시 지침 크기", item=f"{len(env_sum['always'])}개 파일", count=env_sum["always_bytes"],
                         action="어긴 적 없고 다른 데서 막히는 규칙을 상세 파일로 내린다", handoff="retrospective"))

    rate = lambda wt, v: round(v / types[wt]["sessions"], 3) if wt in types else None
    base_cells = {f"{wt}|{st}|{k}": rate(wt, v) for (wt, st, k), v in cells.items()}
    compare = []
    if baseline:
        for k, old in sorted(baseline.get("cells", {}).items(), key=lambda kv: -(kv[1] or 0)):
            wt = k.split("|")[0]
            compare.append(dict(cell=k.replace("|", " · "), before=old,
                                after=base_cells.get(k, 0.0) if wt in types else None))

    ex = read_json(os.path.join(out_dir, "extract_meta.json"), {})
    cx = read_json(os.path.join(out_dir, "context_meta.json"), {})
    data = dict(
        period=dict(since=ex.get("since"), until=ex.get("until"), source=ex.get("source")),
        totals=dict(extracted=len(meta), analyzed=len(rows), by_tool=dict(collections.Counter(r["_meta"]["tool"] for r in rows)),
                    eval_excluded=evals + ex.get("excluded", 0), unknown_ids=unknown, forks=ex.get("forks"),
                    skipped_zst=ex.get("skipped_zst", 0), candidates=cx.get("candidates"),
                    duplicates_removed=cx.get("duplicates_removed"), context_missing=cx.get("missing"),
                    judged=len(judged), corrections=len(corr)),
        types=types, stage_kind=dict(kinds=kinds, rows=stage_rows),
        months=months,
        sessions_by_month=[sum(1 for r in rows if r["_meta"]["start"].startswith(m)) for m in months],
        corr_by_month=[sum(1 for c in corr if c["date"].startswith(m)) for m in months],
        causes=[[k, sum(1 for c in corr if c["cause"] == k)] for k in CAUSES],
        place_loaded=[[p, place_loaded[(p, True)], place_loaded[(p, False)], place_loaded[(p, None)]]
                      for p in ("상시지침", "상세파일", "메모리", "스킬")],
        violated=violated[:15],
        no_rule=[dict(kind=k, count=len(cs), examples=[c["what"] for c in cs[:3]]) for k, cs in sorted(no_rule.items(), key=lambda kv: -len(kv[1]))],
        missing_skills=missing.most_common(),
        env=env_sum, candidates=cand, baseline_compare=compare,
        review=read_json(os.path.join(out_dir, "review.json")),
    )
    base = dict(period=data["period"], sessions={wt: t["sessions"] for wt, t in types.items()}, cells=base_cells)
    return data, base, corr


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--baseline", help="이전 진단의 baseline.json")
    args = p.parse_args(argv)
    baseline = read_json(args.baseline) if args.baseline else None
    data, base, corr = build(args.out_dir, baseline)
    for name, obj in (("report_data.json", data), ("baseline.json", base), ("corrections.json", corr)):
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
    print(json.dumps(data["totals"], ensure_ascii=False))
    print("causes", data["causes"])
    print("candidates", len(data["candidates"]))


if __name__ == "__main__":
    main()
