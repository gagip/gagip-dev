# VSA Godot 아키텍처

> Godot(GDScript) 프로젝트에 적용되는 VSA 규칙.
> 공통 원칙은 `vsa-common-architecture.md` 참조.

---

## 폴더 구조

```
res://
├── app/
│   ├── Main.tscn
│   ├── Main.gd          ← 씬 전환, 진입점 (글루 최소화)
│   └── GameManager.gd   ← 전체 상태 (최소화)
│
├── features/
│   ├── player/
│   │   ├── Player.tscn      ← 씬은 하나
│   │   ├── Player.gd        ← 진입점만 (행동 스크립트에 위임)
│   │   ├── movement/
│   │   │   └── PlayerMovement.gd
│   │   ├── combat/
│   │   │   ├── PlayerCombat.gd
│   │   │   └── AttackData.gd
│   │   ├── inventory/
│   │   │   └── Inventory.gd
│   │   └── shared/          ← 두 번째 슬라이스 생기면 생성
│   │       ├── PlayerStats.tres
│   │       └── PlayerEvents.gd
│   ├── enemy/
│   │   ├── patrol/
│   │   └── attack/
│   ├── ui/
│   │   ├── hud/
│   │   └── main_menu/
│   └── world/
│       ├── level_load/
│       └── save_game/
│
├── shared/
│   ├── autoloads/
│   │   ├── EventBus.gd      ← Signal만 있는 전역 허브
│   │   ├── GameState.gd     ← 전역 상태
│   │   ├── SceneManager.gd  ← 씬 전환
│   │   └── Logger.gd        ← 로깅
│   ├── utils/
│   │   └── GameValidators.gd
│   └── resources/
│       └── ItemDatabase.tres
│
└── assets/               ← 피처와 분리
    ├── sprites/
    ├── sounds/
    └── fonts/
```

---

## 슬라이스 단위

**씬 하나 + 행동별 스크립트 폴더**

```
features/player/
  Player.tscn         ← 씬은 하나 (Godot 에디터 작업 흐름 유지)
  Player.gd           ← 진입점만 — 행동 스크립트에 위임
  movement/
    PlayerMovement.gd ← 이동 로직만
  combat/
    PlayerCombat.gd   ← 전투 로직만
```

### 글루 최소화 원칙

```gdscript
# Player.gd — 연결만 담당, 로직 없음
extends CharacterBody2D

@onready var movement = $Movement
@onready var combat = $Combat

func _physics_process(delta: float) -> void:
    movement.process(delta)     # 위임

func take_damage(amount: float) -> void:
    combat.take_damage(amount)  # 위임
```

---

## Autoload 설계

### EventBus — Signal만 있는 Autoload

```gdscript
# shared/autoloads/EventBus.gd
extends Node

# Signal 이름은 과거형 동사 (일어난 일)
signal player_died()
signal player_health_changed(new_health: int, max_health: int)
signal enemy_killed(enemy_type: String, position: Vector2)
signal item_collected(item_id: String)
signal level_completed(level_index: int)
signal scene_change_requested(scene_key: String)
```

> Signal이 30개 이상이 되면 카테고리별 분리 고려:
> `PlayerEvents.gd`, `EnemyEvents.gd`, `UIEvents.gd`

### GameState — 전역 상태 관리

```gdscript
# shared/autoloads/GameState.gd
extends Node

var current_player_stats: PlayerStats = null
var current_level: int = 1

func get_player_stats() -> PlayerStats:
    return current_player_stats

func update_player_stats(stats: PlayerStats) -> void:
    current_player_stats = stats
    player_stats_changed.emit(stats)

signal player_stats_changed(stats: PlayerStats)
```

### SceneManager — 씬 전환

```gdscript
# shared/autoloads/SceneManager.gd
extends Node

const SCENES = {
    "main_menu": "res://features/ui/main_menu/MainMenu.tscn",
    "game":      "res://features/world/game/Game.tscn",
    "inventory": "res://features/player/inventory/Inventory.tscn",
    "game_over": "res://features/ui/game_over/GameOver.tscn",
}

func go_to(scene_key: String) -> void:
    get_tree().change_scene_to_file(SCENES[scene_key])
```

---

## 슬라이스 간 통신

### 데이터 요청 — Autoload (GameState)

```gdscript
# ✔ Autoload를 통해 데이터 접근
# ✘ 다른 슬라이스 노드 직접 접근 금지

func calculate_damage() -> float:
    var stats = GameState.get_player_stats()
    return stats.attack_power * _combo_multiplier
```

### 이벤트 전파 — EventBus Signal

```gdscript
# 발신 — 수신자를 모름
func take_damage(amount: float) -> void:
    _health -= amount
    EventBus.player_health_changed.emit(_health, MAX_HEALTH)
    if _health <= 0:
        EventBus.player_died.emit()

# 수신 — 발신자를 모름
func _ready() -> void:
    EventBus.player_died.connect(_on_player_died)
    EventBus.player_health_changed.connect(_on_health_changed)
```

### 씬 전환 — SceneManager

```gdscript
# ✔ 씬 키만 앎
SceneManager.go_to("game_over")

# ✘ 씬 경로 하드코딩 금지
# get_tree().change_scene_to_file("res://features/ui/game_over/GameOver.tscn")
```

---

## Cross-cutting Concerns

### 로깅 — Logger Autoload

```gdscript
# shared/autoloads/Logger.gd
extends Node

enum Level { DEBUG, INFO, WARNING, ERROR }

func info(msg: String, context: String = "") -> void:
    _log(Level.INFO, msg, context)

func error(msg: String, context: String = "") -> void:
    _log(Level.ERROR, msg, context)
    EventBus.error_occurred.emit(msg)

# 슬라이스에서 사용
func take_damage(amount: float) -> void:
    Logger.info("Player took %s damage" % amount, "PlayerCombat")
```

### 검증 — assert + GameValidators

```gdscript
# 슬라이스 내부 — assert (디버그 빌드만)
func take_damage(amount: float) -> void:
    assert(amount >= 0, "Damage cannot be negative")
    _health -= amount

# 공통 검증 — shared/utils/GameValidators.gd (순수 함수)
class_name GameValidators

static func is_valid_damage(amount: float) -> bool:
    return amount >= 0 and amount < 9999
```

---

## 테스트

```
핵심 로직: GUT (Godot Unit Test)
전체 흐름: 직접 플레이테스트 (E2E 생태계 미성숙)

test/
  features/player/combat/
    test_player_combat.gd
  features/player/shared/
    test_player_stats.gd
  shared/
    test_game_validators.gd
```

```gdscript
# GUT 테스트 예시
extends GutTest

var combat: PlayerCombat

func before_each() -> void:
    combat = PlayerCombat.new()
    combat._health = 100.0
    add_child(combat)

func test_take_damage_reduces_health() -> void:
    combat.take_damage(30.0)
    assert_eq(combat._health, 70.0)

func test_death_emits_signal() -> void:
    watch_signals(EventBus)
    combat.take_damage(100.0)
    assert_signal_emitted(EventBus, "player_died")
```

---

## 네이밍 컨벤션

| 항목 | 규칙 | 예시 |
| --- | --- | --- |
| 씬 파일 | PascalCase.tscn | `Player.tscn` |
| 스크립트 파일 | PascalCase.gd | `PlayerCombat.gd` |
| 리소스 파일 | PascalCase.tres | `PlayerStats.tres` |
| 폴더명 | snake_case | `features/player/combat/` |
| 테스트 파일 | test_ 접두사 | `test_player_combat.gd` |
| 클래스명 | PascalCase | `class_name PlayerCombat` |
| 변수/함수 | snake_case | `var player_health`, `func take_damage()` |
| Private | _ 접두사 | `var _health`, `func _handle_input()` |
| 상수 | SCREAMING_SNAKE_CASE | `const MAX_HEALTH = 100.0` |
| Signal | snake_case 과거형 | `signal player_died()` |
| Autoload | 역할 명확한 단수 명사 | `EventBus`, `GameState`, `SceneManager` |

### 좋은 이름 vs 나쁜 이름

```
✔ PlayerCombat.gd     — 도메인 + 역할 명확
✔ EnemyPatrol.gd      — 도메인 + 역할 명확
✔ signal player_died  — 과거형, 발생한 일

✘ PlayerManager.gd    — Manager는 쓰레기통 냄새
✘ GameHelper.gd       — Helper도 마찬가지
✘ signal update_hud   — 명령형, 수신자에 결합
```
