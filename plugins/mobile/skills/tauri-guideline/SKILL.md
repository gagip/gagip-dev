---
name: tauri-guideline
description: >
  Tauri v2 모바일 프로젝트(Native↔Rust↔React 3-레이어 브리지)의 아키텍처·디버깅·테스트·플러그인 선택·계약 프로그래밍 가이드라인을 제공하는 스킬.
  "tauri 구조", "Rust랑 React 역할", "레이어 분리", "브리지 디버깅", "tauri 로그 어떻게",
  "mock 빌드", "e2e 전략", "tauri 테스트", "tauri 플러그인 골라줘", "공식 vs 자제작",
  "레이어 경계 검증", "SSOT 어디", "계약 프로그래밍", "타입 어디서 검증" 등의
  표현이 나오면 반드시 이 스킬을 사용할 것.
allowed-tools: Read, Glob, Grep
---

## 목적

이 스킬은 Tauri v2 모바일 앱 개발에서 반복적으로 마주치는 의사결정 질문에 일관된 답을 제공한다.
질문을 받으면 아래 인덱스에서 해당 references 파일을 로드하여 가이드라인을 인용한다.

## 주제별 인덱스

| 주제 | 언제 참조 | 파일 |
|------|-----------|------|
| 레이어 아키텍처·SSOT | Rust/React 역할 구분, 데이터 흐름, 플랫폼 분기 | `$SKILL_DIR/references/architecture.md` |
| 디버깅·로그 | 브리지 추적, tauri-plugin-log 설정, breakpoint 한계 | `$SKILL_DIR/references/debugging.md` |
| 테스트 전략 | mock 빌드, feature flag, e2e, CI | `$SKILL_DIR/references/testing.md` |
| 계약 프로그래밍 | 레이어 경계 검증, 타입 vs 런타임, SSOT | `$SKILL_DIR/references/contracts.md` |
| 플러그인 선택 | 자제작 vs 공식, 카테고리별 우선순위 | `$SKILL_DIR/references/plugins-catalog.md` |

## 작업 순서

1. 질문을 분류하여 위 표에서 관련 references 파일 1~2개를 선택한다.
2. 해당 파일을 로드하고 관련 원칙을 인용한다.
3. 원칙을 사용자의 구체적인 컨텍스트에 적용하여 답한다. 원칙과 사용자 의도가 충돌하면 충돌 사실을 명시한다.

## 행동 원칙

- SSOT는 Rust다. React는 표현 레이어, Kotlin/Swift는 OS 어댑터다.
- 추측하지 않는다. 반드시 references를 먼저 인용하고 그 근거로 답한다.
- ECG·특정 도메인 식별자가 아닌 일반화된 표현(디바이스 페이로드, 네이티브 레이어 등)으로 설명한다.
