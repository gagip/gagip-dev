---
schema_version: "1.0"
name: design-md-required-sections
description: >
  tailwind.config.js와 :root CSS 변수가 있는 브라운필드 스캐폴드에서
  "DESIGN.md 만들어줘"를 요청했을 때, design-md 스킬이 코드를 스캔해
  실제 값을 추출하고 필수 6섹션(Overview, Colors, Typography, Spacing & Layout,
  Components, Do's & Don'ts)을 모두 채운 DESIGN.md를 프로젝트 루트에
  생성하는지 검증한다. 특히 SKILL.md가 "정확도 최대 레버"로 지목한
  Do's & Don'ts가 비어 있지 않은지, 그리고 브라운필드에서는
  preview.html을 기본으로 생성하지 않는지가 핵심이다.
tags: [design-md, structure]
runs: 3
expected_outcome: >
  <root>/DESIGN.md가 생성되고, YAML frontmatter(토큰)와 6개 필수 섹션이 모두
  채워진다. Do's & Don'ts 섹션은 구체적 금지 규칙을 담고 있다. 브라운필드이므로
  사용자가 명시적으로 요청하지 않은 preview.html은 생성되지 않는다.
max_turns: 30
timeout_seconds: 600
allowed_tools: [Bash, Glob, Grep, Read, Write, Edit, AskUserQuestion]
scaffold_script: |
  set -e
  git init -q
  git config user.email "eval@example.com"
  git config user.name "Eval Bot"
  mkdir -p src/styles src/components
  cat > tailwind.config.js <<'EOF'
  module.exports = {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
      extend: {
        colors: {
          primary: "#5A67D8",
          surface: "#FFFFFF",
          ink: "#1A202C",
        },
        fontFamily: {
          sans: ["Inter", "sans-serif"],
        },
        spacing: {
          xs: "4px",
          sm: "8px",
          md: "16px",
          lg: "24px",
          xl: "32px",
        },
      },
    },
  };
  EOF
  cat > src/styles/globals.css <<'EOF'
  :root {
    --color-primary: #5A67D8;
    --color-surface: #FFFFFF;
    --color-ink: #1A202C;
    --font-family-base: 'Inter', sans-serif;
    --radius-md: 8px;
    --space-md: 16px;
  }

  body {
    font-family: var(--font-family-base);
    color: var(--color-ink);
    background: var(--color-surface);
  }
  EOF
  cat > src/components/Button.css <<'EOF'
  .btn-primary {
    background: var(--color-primary);
    border-radius: var(--radius-md);
    padding: 12px 20px;
    height: 44px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  }
  EOF
  git add -A
  git commit -q -m "chore: 초기 디자인 토큰 스캐폴드"
---
DESIGN.md 만들어줘
