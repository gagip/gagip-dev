// light-research 스킬용 Workflow 스크립트 템플릿.
// ANGLES 배열과 synthesis 프롬프트의 출력 구조(섹션 제목)만 주제에 맞게 바꿔서 쓴다.
// 사용법: 이 파일을 통째로 복사한 뒤, meta.name/description과 ANGLES, seedClaims, synthesis 지시문을 교체해서
// Workflow 툴의 `script` 파라미터로 전달한다.

export const meta = {
  name: 'light-research-<주제-슬러그>',
  description: '<주제> 축소 리서치 (검증 라운드 생략)',
  phases: [
    { title: 'Search' },
    { title: 'Synthesize' },
  ],
}

// 탐색 각도는 2~4개로 서로 겹치지 않게 나눈다. 각 프롬프트에는 반드시
// "신뢰할 수 있는 출처 위주로 찾고 URL을 남겨라"를 포함시켜 검증 단계 없이도
// 출처 품질을 1차로 거른다.
const ANGLES = [
  { key: 'angle1', prompt: '<주제>에 대해 <각도1>을 중심으로 조사해라. 신뢰할 수 있는 출처(위키백과, 주요 언론, 1차 인터뷰 등)를 찾아 URL과 핵심 사실을 나열하라.' },
  { key: 'angle2', prompt: '<주제>에 대해 <각도2>을 중심으로 조사해라. 신뢰할 수 있는 출처를 찾아 URL과 핵심 사실을 나열하라.' },
  { key: 'angle3', prompt: '<주제>에 대해 <각도3>을 중심으로 조사해라. 신뢰할 수 있는 출처를 찾아 URL과 핵심 사실을 나열하라.' },
]

const SEARCH_SCHEMA = {
  type: 'object',
  properties: {
    facts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          fact: { type: 'string' },
          url: { type: 'string' },
        },
        required: ['fact', 'url'],
      },
    },
  },
  required: ['facts'],
}

// Search와 Fetch를 분리하지 않는다 — 각 에이전트가 WebSearch+WebFetch를 스스로 조합해
// fact+url 쌍을 바로 반환하게 한다. deep-research 대비 에이전트 수를 절반 이하로 줄이는 핵심.
const searchResults = await parallel(ANGLES.map(a => () =>
  agent(a.prompt, { label: `search:${a.key}`, phase: 'Search', schema: SEARCH_SCHEMA })
))

const allFacts = searchResults.filter(Boolean).flatMap((r, i) =>
  r.facts.map(f => ({ ...f, angle: ANGLES[i].key }))
)

log(`검색 완료: ${allFacts.length}개 사실 수집`)

// 이전 대화에서 이미 신뢰도 높게 확보된 사실이 있으면 여기 채워 넣는다 (없으면 빈 배열).
// 중복 검색을 줄이고, synthesis 단계에서 "기존 검증된 사실"과 "이번에 새로 모은 사실"을 구분해서 다룰 수 있게 한다.
const seedClaims = []

// 종합은 barrier 이후 1개 에이전트로 끝낸다 — 검증 단계가 없으므로 파이프라인으로 나눌 이유가 없다.
const synthesis = await agent(
  `아래는 <주제>에 대해 수집된 사실들이다. 이를 종합해 한국어로 지식 노트를 작성하라.

기존 검증된 사실(재사용, 신뢰도 높음):
${JSON.stringify(seedClaims, null, 2)}

이번 검색에서 수집한 사실(출처 URL 포함, 개별 검증은 생략됨 — 명백히 신뢰도 낮은 출처는 배제하고 사용):
${JSON.stringify(allFacts, null, 2)}

다음 구조로 마크다운 본문을 작성하라 (frontmatter 제외, 본문만):
## <섹션1>
## <섹션2>
## <섹션3>

각 항목은 구체적 사실/발언 중심으로 서술하고, 문장 끝에 출처 URL을 괄호로 표기하라.
확인되지 않은 추측성 내용은 포함하지 마라.`,
  { label: 'synthesize', phase: 'Synthesize' }
)

return { seedClaims, allFacts, synthesis }
