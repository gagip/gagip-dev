"""GitHub 관련 기능 (Git + GitHub API)"""

import json
import sys

from utils import run_command


def get_current_branch() -> str:
    """현재 Git 브랜치명을 반환합니다.

    Returns:
        현재 브랜치명
    """
    return run_command(["git", "branch", "--show-current"])


GRAPHQL_QUERY = """
query($owner: String!, $repo: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          comments(first: 100) {
            nodes {
              path
              body
              author {
                login
              }
              line
              position
            }
          }
        }
      }
    }
  }
}
"""


def get_pr_number(branch: str) -> str:
    """특정 브랜치의 PR 번호를 가져옵니다.

    Args:
        branch: 브랜치명

    Returns:
        PR 번호 (문자열)

    Raises:
        SystemExit: PR을 찾지 못한 경우
    """
    result = run_command([
        "gh", "pr", "list",
        "--head", branch,
        "--json", "number",
        "--jq", ".[0].number"
    ])

    if not result:
        print(f"❌ Error: No PR found for branch '{branch}'", file=sys.stderr)
        sys.exit(1)

    return result


def get_pr_info(pr_number: str) -> dict:
    """PR의 기본 정보를 가져옵니다.

    Args:
        pr_number: PR 번호

    Returns:
        PR 정보 딕셔너리 (title, createdAt, url)
    """
    result = run_command([
        "gh", "pr", "view", pr_number,
        "--json", "title,createdAt,url"
    ])
    return json.loads(result)


def get_repository_info() -> tuple[str, str]:
    """현재 저장소의 owner와 name을 가져옵니다.

    Returns:
        (owner, repo) 튜플
    """
    result = run_command(["gh", "repo", "view", "--json", "owner,name"])
    data = json.loads(result)
    owner = data["owner"]["login"]
    repo = data["name"]
    return owner, repo


def fetch_review_threads(owner: str, repo: str, pr_number: str) -> list[dict]:
    """GraphQL API를 사용하여 PR의 리뷰 스레드를 가져옵니다 (페이지네이션 지원).

    Args:
        owner: 저장소 소유자
        repo: 저장소명
        pr_number: PR 번호

    Returns:
        리뷰 스레드 리스트
    """
    all_threads = []
    cursor = None

    while True:
        cmd = [
            "gh", "api", "graphql",
            "-f", f"query={GRAPHQL_QUERY}",
            "-F", f"owner={owner}",
            "-F", f"repo={repo}",
            "-F", f"number={pr_number}",
        ]
        if cursor:
            cmd += ["-f", f"cursor={cursor}"]

        result = run_command(cmd)
        data = json.loads(result)
        review_threads = (
            data
            .get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
        )

        all_threads.extend(review_threads.get("nodes", []))

        page_info = review_threads.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return all_threads


def extract_comments_from_threads(
        threads: list[dict],
        include_resolved: bool = False
) -> list[dict]:
    """리뷰 스레드에서 코멘트를 추출합니다.

    Args:
        threads: 리뷰 스레드 리스트
        include_resolved: resolved 코멘트 포함 여부

    Returns:
        코멘트 리스트
    """
    comments = []

    for thread in threads:
        is_resolved = thread.get("isResolved", False)

        # resolved 필터링
        if not include_resolved and is_resolved:
            continue

        # 스레드 내 모든 코멘트 추출
        thread_comments = thread.get("comments", {}).get("nodes", [])
        for comment in thread_comments:
            comments.append({
                "thread_id": thread.get("id"),
                "path": comment.get("path"),
                "body": comment.get("body"),
                "user": comment.get("author", {}).get("login", "Unknown"),
                "line": comment.get("line"),
                "position": comment.get("position"),
                "is_resolved": is_resolved
            })

    return comments


def get_pr_comments(pr_number: str, include_resolved: bool = False) -> list[dict]:
    """PR의 코멘트를 가져옵니다.

    Args:
        pr_number: PR 번호
        include_resolved: resolved 코멘트 포함 여부

    Returns:
        코멘트 리스트
    """
    # 1. 저장소 정보 가져오기
    owner, repo = get_repository_info()

    # 2. GraphQL로 review thread 가져오기
    threads = fetch_review_threads(owner, repo, pr_number)

    # 3. 코멘트 추출 및 필터링
    comments = extract_comments_from_threads(threads, include_resolved)

    return comments
