// trip-spot-research 스킬용 Workflow 스크립트 템플릿.
// SPOTS/TARGET_DATES/DEST_DB_URL과 각도별 프롬프트만 실제 여행지에 맞게 바꿔서 쓴다.
// 노션(또는 다른 DB) 반영이 필요 없으면 notion-schema 각도와 Notion Update 단계를 통째로 지운다.
// 신규 후보 발굴이나 지역 이벤트 확인이 필요 없으면 해당 각도만 빼면 된다 — 나머지 구조는 그대로 둔다.
//
// 사용법: 이 파일을 통째로 복사해서 meta, SPOTS, TARGET_DATES, DEST_DB_URL, 각 각도 프롬프트를
// 실제 여행지·스팟 목록·날짜로 교체한 뒤 Workflow 툴의 script 파라미터로 전달한다.

export const meta = {
  name: 'trip-spot-research-<여행지-슬러그>',
  description: '<여행지> 스팟 휴무/영업시간 확인, 후기 보강, (선택)신규후보 발굴 후 (선택)DB 반영',
  phases: [
    { title: 'Research', detail: '휴무확인/후기보강/(선택)신규후보/(선택)DB스키마 각도 병렬 조사' },
    { title: 'Synthesize', detail: '조사 결과를 스팟별로 종합' },
    { title: 'Reflect', detail: '(선택) 종합 결과를 대상 DB에 반영' },
  ],
}

// id, name, category, address, hours_open, hours_close, closed_days, hours_notes 등
// 기존에 파악된 필드를 그대로 넣는다. 필드가 없으면 null로 채워도 된다 — 리서치 단계에서 처음부터 확인한다.
const SPOTS = [
  // { id: 'example-spot', name: '예시 스팟', category: 'restaurant', address: null, hours_open: null, hours_close: null, closed_days: [], hours_notes: null },
]

// 요일까지 미리 계산해서 넣어준다 (스크립트 안에서는 Date를 쓸 수 없음).
const TARGET_DATES = [
  // { date: '2026-08-08', weekday: '토요일' },
  // { date: '2026-08-09', weekday: '일요일' },
]

// 노션 등 반영 대상이 없으면 빈 문자열로 두고, notion-schema 각도와 Reflect 단계를 지운다.
const DEST_DB_URL = ''

const CLOSED_DAYS_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          status_by_date: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                date: { type: 'string' },
                status: { type: 'string', enum: ['open', 'closed', 'unknown'] },
              },
              required: ['date', 'status'],
            },
          },
          verified_hours: { type: 'string' },
          note: { type: 'string' },
        },
        required: ['id', 'status_by_date'],
      },
    },
  },
  required: ['results'],
}

const REVIEWS_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          blog_quotes: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                source_title: { type: 'string' },
                url: { type: 'string' },
                quote: { type: 'string' },
              },
            },
          },
          summary: { type: 'string' },
        },
        required: ['id', 'summary'],
      },
    },
  },
  required: ['results'],
}

const CANDIDATES_SCHEMA = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          category: { type: 'string' },
          address: { type: 'string' },
          why_recommended: { type: 'string' },
          open_on_target_dates: { type: 'string', enum: ['open', 'closed', 'unknown'] },
          source_url: { type: 'string' },
        },
        required: ['name', 'category', 'why_recommended'],
      },
    },
  },
  required: ['candidates'],
}

const DB_SCHEMA_SCHEMA = {
  type: 'object',
  properties: {
    database_found: { type: 'boolean' },
    data_source_id: { type: 'string' },
    properties: {
      type: 'array',
      items: { type: 'object', properties: { name: { type: 'string' }, type: { type: 'string' } } },
    },
    notes: { type: 'string' },
  },
  required: ['database_found'],
}

phase('Research')

const researchAgents = [
  () => agent(
    `다음 스팟 목록의 실제 영업 여부를 대상 날짜 기준으로 확인해줘.
대상 날짜: ${JSON.stringify(TARGET_DATES)}
스팟 목록: ${JSON.stringify(SPOTS)}

네이버플레이스/카카오맵/공식 홈페이지·블로그를 검색해서 각 스팟마다:
- 정기휴무일이 대상 날짜 요일과 겹치는지
- 계절 임시휴무(여름 휴가철 등) 공지가 있는지
- hours_open/hours_close/closed_days가 null이거나 불확실하면 실제 값을 찾아 채울 것
- 예약이 필요한 곳은 예약 필수 여부와 마감 가능성도 note에 남길 것
기존 DB 값과 실제 확인값이 다르면 note에 "기존값 → 실제값" 형태로 반드시 표시해줘.
각 스팟의 status_by_date를 대상 날짜별로 open/closed/unknown 중 하나로 판정해줘.`,
    { label: 'closed-days', phase: 'Research', schema: CLOSED_DAYS_SCHEMA }
  ),
  () => agent(
    `다음 스팟 목록에 대해 티스토리·네이버블로그 등 개인 블로그 후기를 우선으로 검색해서(공식 홍보 콘텐츠보다 실제 방문 후기 우선) 최근 방문 후기를 모아줘.
스팟 목록: ${JSON.stringify(SPOTS.map(s => ({ id: s.id, name: s.name, category: s.category })))}

스팟마다 인용 가능한 블로그 글 1~3개(출처 제목/URL/짧은 인용문)와 2~3문장 요약(summary)을 만들어줘.
검색이 잘 안 되는 스팟은 summary에 "후기 확인 어려움"이라고 명시해.`,
    { label: 'reviews', phase: 'Research', schema: REVIEWS_SCHEMA }
  ),
  // 신규 후보 발굴이 필요 없으면 이 각도를 지운다.
  () => agent(
    `<지역/카테고리>를 중심으로, 아래 기존 스팟 목록에는 없는 신규 후보를 찾아줘.
이미 있는 스팟(제외 대상): ${JSON.stringify(SPOTS.map(s => s.name))}

티스토리/네이버블로그 최신 후기 위주로 검색해서 5~10곳 정도 찾아줘.
각 후보에 대해 이름/카테고리/주소/추천 이유/대상 날짜(${JSON.stringify(TARGET_DATES.map(d => d.date))}) 영업 가능 여부(가능하면 확인)/출처 URL을 정리해줘.`,
    { label: 'new-candidates', phase: 'Research', schema: CANDIDATES_SCHEMA }
  ),
  // 반영 대상 DB가 없으면 이 각도를 지운다.
  () => agent(
    `${DEST_DB_URL} 에서 대상 데이터베이스를 찾아줘.
검색/조회 도구를 사용해서 이 데이터베이스를 열고, 어떤 속성(property)들이 있는지(이름과 타입) 확인해줘.
이후 단계에서 이 스키마에 맞춰 새 항목을 추가하거나 기존 항목을 업데이트할 예정이니, data_source_id(또는 database_id)와 속성 목록을 정확히 리턴해줘.`,
    { label: 'db-schema', phase: 'Research', schema: DB_SCHEMA_SCHEMA, agentType: 'general-purpose' }
  ),
]

const [closedDays, reviews, candidates, dbSchema] = await parallel(researchAgents)

log(`조사 완료 — 휴무확인 ${closedDays?.results?.length ?? 0}곳, 후기 ${reviews?.results?.length ?? 0}곳, 신규후보 ${candidates?.candidates?.length ?? 0}곳`)

phase('Synthesize')
const synthesis = await agent(
  `아래는 스팟 리서치 결과야. 대상 날짜: ${JSON.stringify(TARGET_DATES)}

[1] 영업여부 조사 결과: ${JSON.stringify(closedDays)}
[2] 블로그 후기 조사 결과: ${JSON.stringify(reviews)}
[3] 신규 후보 스팟: ${JSON.stringify(candidates)}
[4] 대상 DB 스키마: ${JSON.stringify(dbSchema)}

id를 기준으로 [1]과 [2]를 머지해서 스팟별 업데이트 목록(spots_update)을 만들고, [3]은 new_candidates로 분리해줘.
각 spots_update 항목에는 id, name, status_by_date, is_available(대상 날짜 전부 open이면 true), review_summary, blog_quotes(있으면)를 포함해줘.
executive_summary(3~5문장)를 맨 앞에 만들고, 대상 날짜에 휴무라서 못 가는 곳이 있으면 반드시 첫 문장에 언급해줘.`,
  {
    label: 'synthesize',
    phase: 'Synthesize',
    schema: {
      type: 'object',
      properties: {
        executive_summary: { type: 'string' },
        spots_update: { type: 'array', items: { type: 'object' } },
        new_candidates: { type: 'array', items: { type: 'object' } },
        db_schema: { type: 'object' },
      },
      required: ['executive_summary', 'spots_update'],
    },
  }
)

log('종합 완료')

// 반영 대상 DB가 없으면 아래 Reflect 단계를 통째로 지우고 synthesis를 그대로 return한다.
phase('Reflect')
const reflectResult = await agent(
  `${DEST_DB_URL} 에 아래 종합 리서치 결과를 반영해줘.
DB 스키마 정보: ${JSON.stringify(synthesis.db_schema)}
반영할 데이터: ${JSON.stringify({ spots_update: synthesis.spots_update, new_candidates: synthesis.new_candidates })}

기존 항목은 이름으로 찾아서 조사 결과를 해당 속성에 업데이트하고, 신규 후보는 스키마에 맞춰 새 항목으로 생성해줘.
짧은 필드(태그, 한두 문장 팁)는 그대로 반영하되, 인용문·URL이 섞인 긴 텍스트 필드는 쓰는 과정에서 드물게
음절이 깨지는 인코딩 이슈가 있을 수 있으니, 쓴 직후 다시 읽어서 깨졌으면 한 번만 재시도하고 그래도
깨지면 무리해서 반복하지 말고 "직접 확인 필요"로 남겨줘.
완료 후 몇 개를 업데이트했고 몇 개를 새로 만들었는지 정리해서 알려줘.`,
  { label: 'reflect', phase: 'Reflect', agentType: 'general-purpose' }
)

return {
  executive_summary: synthesis.executive_summary,
  spots_update: synthesis.spots_update,
  new_candidates: synthesis.new_candidates,
  reflect_result: reflectResult,
}
