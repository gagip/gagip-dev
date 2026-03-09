"""코멘트 포맷팅 관련 기능"""


def format_header(pr_info: dict) -> list[str]:
    """PR 헤더 정보를 포맷팅합니다.

    Args:
        pr_info: PR 정보 딕셔너리

    Returns:
        포맷팅된 헤더 문자열 리스트
    """
    return [
        "# Code Review Comments\n",
        f"> PR #{pr_info.get('number', 'N/A')}: {pr_info['title']}",
        f"> Date: {pr_info['createdAt']}",
        f"> URL: {pr_info['url']}\n",
        "---\n"
    ]


def format_single_comment(idx: int, comment: dict) -> list[str]:
    """단일 코멘트를 포맷팅합니다.

    Args:
        idx: 코멘트 번호
        comment: 코멘트 딕셔너리

    Returns:
        포맷팅된 코멘트 문자열 리스트
    """
    file_path = comment.get('path', 'Unknown')
    line = comment.get('line') or comment.get('position')
    line_info = f" (Line: {line})" if line else ""
    user = comment.get('user', 'Unknown')
    body = comment.get('body', '').strip().replace("\n", "\n> ")

    thread_id = comment.get('thread_id', '')

    return [
        f"## Review Comment #{idx}\n",
        f"### 파일: `{file_path}`{line_info}\n",
        f"**작성자**: @{user}\n",
        f"**Thread ID**: `{thread_id}`\n",
        f"**원문 코멘트**:\n> {body}\n",
        "---\n"
    ]


def format_comments(pr_info: dict, comments: list[dict]) -> str:
    """코멘트를 포맷팅하여 마크다운 문자열로 반환합니다.

    Args:
        pr_info: PR 정보 딕셔너리
        comments: 코멘트 리스트

    Returns:
        포맷팅된 마크다운 문자열
    """
    output = []

    # 헤더 추가
    output.extend(format_header(pr_info))

    # 코멘트가 없는 경우
    if not comments:
        output.append("## 코멘트 없음\n")
        output.append("이 PR에는 아직 코드 리뷰 코멘트가 없습니다.")
        return "\n".join(output)

    # 각 코멘트 추가
    for idx, comment in enumerate(comments, start=1):
        output.extend(format_single_comment(idx, comment))

    return "\n".join(output)
