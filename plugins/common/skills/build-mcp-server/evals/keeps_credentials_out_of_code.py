"""keeps_credentials_out_of_code — 자격 증명이 코드 폴더 밖에, 대화 밖에서 만들어진다.

언어·프레임워크를 가정하지 않는다. 스킬 없이 만들어도 좁은 도구·입력 검증은 꽤 잘 나오지만,
자격 증명을 코드 폴더의 `.env` 와 환경변수로 처리하는 쪽으로 기우는 경향이 있다. 환경변수에
토큰이 남으면 같은 API 를 셸에서 그대로 부를 수 있어 좁히기 자체가 무효가 된다 — 이 케이스는
거기를 본다.

서버 파일 여러 개를 만드는 케이스라 러너 기본 제한시간(300초)으로는 빠듯하다.
`--timeout 600` 으로 돌린다.
"""

PROMPT = (
    "토큰 하나로 인증하는 사내 상태 API 를 MCP 서버로 감싸줘. "
    "읽기 전용이고 'deploy' 항목만 열면 돼. ./statusmcp 폴더에 파일만 만들고 "
    "등록은 하지 마. 토큰은 아직 없으니 나중에 내가 직접 넣을게."
)
RUNS = 2

SKIP = "--exclude-dir=node_modules --exclude-dir=.git"


def check(ctx):
    # 실질 검사를 먼저 둔다 — 발동 여부를 앞에 두면 baseline(스킬 없이 실행)이 첫 줄에서
    # 멈춰 버려, 스킬이 실제로 무엇을 더 해내는지 대조가 안 된다.
    tree = ctx.sh("find statusmcp -type f -not -path '*/node_modules/*'").stdout
    assert tree.strip(), "statusmcp 폴더에 파일이 없음"

    # 자격 증명은 코드 폴더가 아니라 사용자 설정 폴더에 둔다. 폴더째 공유·업로드해도
    # 따라가지 않게 하려는 것이다.
    in_config = ctx.sh(f"grep -rIl {SKIP} '[.]config/' statusmcp || true").stdout
    assert in_config.strip(), "자격 증명을 ~/.config 아래 두지 않음 (코드 폴더·환경변수에 의존)"

    # 소유자만 읽도록 권한을 조인다.
    tightened = ctx.sh(
        f"grep -rIl {SKIP} -e chmod -e 0600 -e 0o600 -e S_IRUSR statusmcp || true"
    ).stdout
    assert tightened.strip(), "자격 증명 파일 권한을 조이지 않음"

    # 코드 폴더에 실제 비밀 파일이 남으면 안 된다 (.env.example 같은 빈 템플릿은 무해).
    assert not ctx.exists("statusmcp/.env"), "서버 폴더에 .env 가 있음"
    assert not ctx.exists("statusmcp/*credential*"), "서버 폴더에 자격 증명 파일이 있음"
    assert not ctx.exists("statusmcp/*token*"), "서버 폴더에 토큰 파일이 있음"

    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
