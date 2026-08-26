#!/usr/bin/env python3

"""GitHub PR 코멘트를 가져와서 CODE_REVIEW.md 파일로 정리하는 스크립트"""

import sys

from formatter import format_comments
from github_api import get_current_branch, get_pr_number, get_pr_info, get_pr_comments


def main():
    """메인 실행 함수"""
    # 현재 브랜치 확인
    current_branch = get_current_branch()
    print(f"📍 Current branch: {current_branch}", file=sys.stderr)

    # PR 번호 찾기
    pr_number = get_pr_number(current_branch)
    print(f"🔍 Found PR #{pr_number}", file=sys.stderr)

    # PR 정보 가져오기
    pr_info = get_pr_info(pr_number)
    pr_info['number'] = pr_number

    # PR 코멘트 가져오기 (unresolved만)
    print(f"Fetching unresolved comments...", file=sys.stderr)
    comments = get_pr_comments(pr_number, include_resolved=False)
    print(f"Found {len(comments)} unresolved comment(s)\n", file=sys.stderr)

    # 코멘트 포맷팅 및 출력
    formatted_output = format_comments(pr_info, comments)
    print(formatted_output)


if __name__ == "__main__":
    main()
