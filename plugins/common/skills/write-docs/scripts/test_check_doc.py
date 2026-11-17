from check_doc import find_hits


def kinds(text):
    return [kind for _, kind, _ in find_hits(text)]


def test_finds_internal_expressions_in_body():
    text = "\n".join(
        [
            "- src/alarm.ts 참고",
            "- /Users/a/b",
            "- #628에서 고침",
            "- 상태 H3일 때",
            "- 10/16 시안 비평 반영",
            "- 사실표 3줄",
        ]
    )
    assert kinds(text) == ["파일 이름", "로컬 경로", "PR·이슈 번호", "항목 코드", "날짜 꼬리표", "세션 표현"]


def test_skips_dev_note_section_until_next_same_level_heading():
    text = "## 개발 참고\n- src/alarm.ts\n### 파일\n- a.py\n## 범위 외\n- b.py\n"
    assert [number for number, _, _ in find_hits(text)] == [6]


def test_skips_folded_block():
    assert find_hits("<details>\nsrc/x.py\n</details>\n") == []
    assert kinds("<details>\nsrc/x.py\n</details>\nsrc/y.py\n") == ["파일 이름"]


def test_unclosed_fold_is_reported():
    assert kinds("<details>\nsrc/x.py\n") == ["닫히지 않은 접힘"]


def test_finds_code_names_and_dated_review_tag():
    assert kinds("- save_alarm 호출\n- DEFAULT_TIME 값\n- 2026-10-16 회의 결과\n") == ["코드 이름", "코드 이름", "날짜 꼬리표"]


def test_product_values_pass():
    text = "- iOS 17 이상, UTF-8, SHA-256, MP4, Node.js 기반, 색 #1a1a1a, 오전 8:12, 3/4 완료, 2026-10-23 기준\n"
    assert find_hits(text) == []
