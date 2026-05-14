# CHANGELOG

## [0.1.0] - 2026-05-14

### ✨ New Features

- **tauri-guideline**: Tauri v2 모바일 개발 가이드라인 스킬 초기 추가
  - `references/architecture.md`: 3-레이어 구조, 레이어별 역할, SSOT 원칙, 데이터 흐름 패턴
  - `references/debugging.md`: 멀티 레이어 로그 전략, tauri-plugin-log 설정, 브리지 체크포인트
  - `references/testing.md`: Mock e2e 우선 전략, 플랫폼별 mock 빌드(Flavor/Scheme/feature flag), CI 파이프라인
  - `references/contracts.md`: 레이어별 계약 프로그래밍(Kotlin require, Rust Result+뉴타입, React 방어적 렌더링)
  - `references/plugins-catalog.md`: 공식·커뮤니티 플러그인 우선순위표, 자제작 vs 공식 판단 기준

### 📝 Notes

- ECG 도메인 예시를 일반화(디바이스 페이로드, 네이티브 레이어 등)
- ECG 앱 개요 문서의 "기능 요구사항" 및 "분리→모노레포 진화 전략" 섹션은 이번 범위에서 제외
