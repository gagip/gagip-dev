"""반복 검토 루프의 회차 기록. 회차 상한, 이미 바꾼 대상의 재변경, 걸린 장치를 파일 하나에 남기고 코드로 판정한다.

  init <기록> --max-rounds N --guards 이름,이름,...   기록 파일을 만든다
  start <기록>                      다음 회차를 연다. 상한을 넘으면 멈춤
  check <기록> <대상> --severity high|medium|low
                                    지적을 반영해도 되는지 판정한다. 앞 회차에 바꾼 대상은
                                    높음이 아니면 반영하지 않고, 높음이면 사람에게 올린다
  change <기록> <대상...>            이번 회차에 바꾼 대상을 남긴다
  guard <기록> <장치> --fired|--quiet --note "상황 한 줄"
  end <기록> --high N --medium N    회차를 닫고 다음 회차·끝·멈춤을 판정한다
  report <기록>                     회차별 바뀐 대상 수와 걸린 장치 표를 찍는다

종료 코드: 0 진행, 3 멈추고 사람에게 올림, 2 실행 오류(기록 파일·인자 문제).
"""
import argparse
import json
import sys
from pathlib import Path

STOP = 3


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def current(data):
    if not data["rounds"] or data["rounds"][-1]["closed"]:
        raise ValueError("열린 회차가 없음. start를 먼저 부른다")
    return data["rounds"][-1]


def changed_before(data):
    return {t for r in data["rounds"] if r["closed"] for t in r["changed"]}


def cmd_init(a):
    if Path(a.ledger).exists():
        raise ValueError(f"{a.ledger}: 이미 있음")
    guards = [g.strip() for g in a.guards.split(",") if g.strip()]
    if a.max_rounds < 1 or not guards:
        raise ValueError("--max-rounds는 1 이상, --guards는 하나 이상")
    save(a.ledger, {"max_rounds": a.max_rounds, "guards": guards, "rounds": []})
    print(f"기록 시작: 상한 {a.max_rounds}회, 장치 {len(guards)}개")
    return 0


def cmd_start(a):
    data = load(a.ledger)
    if data["rounds"] and not data["rounds"][-1]["closed"]:
        raise ValueError(f"{data['rounds'][-1]['n']}회차가 아직 열려 있음")
    if data["rounds"] and data["rounds"][-1].get("verdict") == "끝":
        raise ValueError("이미 끝난 루프")
    n = len(data["rounds"]) + 1
    if n > data["max_rounds"]:
        print(f"멈춤: 상한 {data['max_rounds']}회를 넘는 {n}회차")
        return STOP
    data["rounds"].append({"n": n, "changed": [], "guards": {}, "closed": False})
    save(a.ledger, data)
    print(f"{n}회차 시작")
    return 0


def cmd_check(a):
    data = load(a.ledger)
    current(data)
    if a.severity == "low":
        print(f"반영 안 함: {a.target}은 낮음. 끝 보고에 모은다")
        return 0
    if a.target not in changed_before(data):
        print(f"반영 가능: {a.target}")
        return 0
    if a.severity == "high":
        print(f"멈춤: 앞 회차에 바꾼 {a.target}에 높음 지적. 두 번째 변경은 사람이 정한다")
        return STOP
    print(f"반영 안 함: {a.target}은 앞 회차에 바꿔 확정됨. 끝 보고의 정할 것으로 모은다")
    return 0


def cmd_change(a):
    data = load(a.ledger)
    r = current(data)
    again = sorted(set(a.targets) & changed_before(data))
    if again and not a.approved:
        print(f"멈춤: 앞 회차에 바꾼 대상을 다시 바꾸려 함 {again}. 사람이 승인했으면 --approved를 붙인다")
        return STOP
    r["changed"] = sorted(set(r["changed"]) | set(a.targets))
    save(a.ledger, data)
    print(f"{r['n']}회차 바뀐 대상 {len(r['changed'])}개")
    return 0


def cmd_guard(a):
    data = load(a.ledger)
    r = current(data)
    if a.name not in data["guards"]:
        raise ValueError(f"{a.name}: init에 없는 장치. 있는 장치: {', '.join(data['guards'])}")
    r["guards"][a.name] = {"fired": a.fired, "note": a.note}
    save(a.ledger, data)
    return 0


def cmd_end(a):
    if a.high < 0 or a.medium < 0:
        raise ValueError("--high·--medium은 0 이상")
    data = load(a.ledger)
    r = current(data)
    missing = [g for g in data["guards"] if g not in r["guards"]]
    if missing:
        raise ValueError(f"{r['n']}회차에 기록하지 않은 장치: {', '.join(missing)}. 안 걸렸으면 --quiet로 남긴다")
    r["findings"] = {"high": a.high, "medium": a.medium}
    r["closed"] = True
    if a.high + a.medium == 0:
        r["verdict"] = "끝"
        code, msg = 0, f"끝: {r['n']}회차에 높음·중간 0건"
    elif r["n"] >= data["max_rounds"]:
        r["verdict"] = "멈춤"
        code, msg = STOP, f"멈춤: 상한 {data['max_rounds']}회에 높음 {a.high}·중간 {a.medium}건이 남음"
    else:
        r["verdict"] = "다음 회차"
        code, msg = 0, f"다음 회차: 높음 {a.high}·중간 {a.medium}건"
    save(a.ledger, data)
    print(msg)
    return code


def cmd_report(a):
    data = load(a.ledger)
    rounds = data["rounds"]
    print("| 장치 | " + " | ".join(f"{r['n']}회차" for r in rounds) + " |")
    print("|---|" + "---|" * len(rounds))
    for g in data["guards"]:
        cells = []
        for r in rounds:
            e = r["guards"].get(g)
            cells.append("-" if e is None else ("걸림" if e["fired"] else "안 걸림") + (f": {e['note']}" if e["note"] else ""))
        print(f"| {g} | " + " | ".join(cells) + " |")
    print("| 바뀐 대상 수 | " + " | ".join(str(len(r["changed"])) for r in rounds) + " |")
    print("| 판정 | " + " | ".join(r.get("verdict", "진행 중") for r in rounds) + " |")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("ledger")
    p.add_argument("--max-rounds", type=int, required=True)
    p.add_argument("--guards", required=True)
    for name in ("start", "report"):
        sub.add_parser(name).add_argument("ledger")
    p = sub.add_parser("check")
    p.add_argument("ledger")
    p.add_argument("target")
    p.add_argument("--severity", choices=("high", "medium", "low"), required=True)
    p = sub.add_parser("change")
    p.add_argument("ledger")
    p.add_argument("targets", nargs="+")
    p.add_argument("--approved", action="store_true")
    p = sub.add_parser("guard")
    p.add_argument("ledger")
    p.add_argument("name")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--fired", action="store_true")
    group.add_argument("--quiet", action="store_true")
    p.add_argument("--note", default="")
    p = sub.add_parser("end")
    p.add_argument("ledger")
    p.add_argument("--high", type=int, required=True)
    p.add_argument("--medium", type=int, required=True)
    a = ap.parse_args(argv)
    return globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"실행 오류: {e}", file=sys.stderr)
        sys.exit(2)
