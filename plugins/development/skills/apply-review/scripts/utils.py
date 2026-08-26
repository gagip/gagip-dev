"""공통 유틸리티 함수"""

import subprocess
import sys


def run_command(cmd: list[str]) -> str:
    """서브프로세스 명령어를 실행하고 결과를 반환합니다.

    Args:
        cmd: 실행할 명령어 리스트

    Returns:
        명령어 실행 결과 (stdout)

    Raises:
        SystemExit: 명령어 실행 실패 시
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)
