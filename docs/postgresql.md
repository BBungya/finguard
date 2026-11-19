# 거래와 판단 결과를 PostgreSQL에 저장하기

PostgreSQL을 거래 원본과 판단 결과의 기준 저장소로 사용합니다. API를 재시작해도 이전 거래가 다음 판단에 반영됩니다. `REDIS_URL`을 설정하면 [Redis 카드 이력 공유](redis_history.md)를 사용하고, 캐시가 없거나 오래되면 DB에서 다시 계산합니다.

## Windows 준비

1. [Docker Desktop 공식 안내](https://docs.docker.com/desktop/setup/install/windows-install/)에서 Windows용 설치 파일을 받습니다.
2. WSL 2 백엔드를 사용해 설치하고, 안내가 나오면 재부팅합니다.
3. Docker Desktop을 실행하고 엔진이 시작될 때까지 기다립니다.
4. 새 PowerShell에서 아래 명령으로 확인합니다.

```powershell
docker version
docker compose version
```

WSL이 없다면 관리자 PowerShell에서 `wsl --install`을 실행한 뒤 재부팅합니다. 이미 설치되어 있다면 `wsl --update`로 업데이트할 수 있습니다. 자세한 순서는 [Microsoft WSL 설치 안내](https://learn.microsoft.com/en-us/windows/wsl/install)를 참고합니다.

PostgreSQL은 아래 Compose 명령이 내려받아 실행하므로 Windows에 따로 설치하지 않아도 됩니다.

## DB와 API 시작

저장소 루트의 PowerShell에서 실행합니다. 이미 있는 `.env`는 덮어쓰지 않습니다.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --wait postgres redis
uv run --env-file .env --locked --group api python -m finguard.database
uv run --env-file .env --locked --group api uvicorn finguard.api:app --host 127.0.0.1 --port 8000 --workers 1
```

기존 `.env`가 있다면 `.env.example`의 `POSTGRES_PASSWORD`와 `DATABASE_URL` 항목을 추가합니다. 예시 비밀번호는 로컬 개발용입니다. 비밀번호를 바꾸면 연결 주소도 함께 바꾸며, 연결 주소에 들어가는 특수문자는 URL 인코딩합니다. DB 볼륨을 이미 만든 뒤 비밀번호 설정만 바꿔도 기존 DB 비밀번호가 자동으로 변경되지는 않습니다.

첫 번째 명령은 `.env`를 준비하고, 두 번째는 DB를 시작합니다. 세 번째는 저장 테이블을 준비하며 다시 실행해도 기존 거래를 지우지 않습니다. 마지막은 API를 실행합니다. #8의 로컬 모델 파일도 필요하며, 준비 방법은 [API 문서](score_api.md)에 있습니다.

브라우저에서 `http://127.0.0.1:8000/docs`를 열고 거래를 보냅니다. `DATABASE_URL`이 없거나 비어 있으면 기존 메모리 모드로 동작합니다. 주소를 지정했는데 DB가 연결되지 않으면 503을 반환합니다. 이때 메모리 모드로 전환하지 않습니다.

DB를 정지할 때는 `docker compose stop postgres`, 다시 시작할 때는 `docker compose up -d --wait postgres`를 실행합니다. 데이터는 이름 있는 볼륨에 남습니다.

## 저장 구조

`scored_transactions` 한 행에 거래와 당시 API 응답을 함께 저장합니다.

| 항목 | 의미 |
| --- | --- |
| `sequence` | 같은 시각 거래의 처리 순서 |
| `transaction_id` | 중복할 수 없는 거래 ID |
| `card_id`, `occurred_at`, `amount`, `category` | 카드 ID, 원본 거래 시각, 정확한 금액, 업종 |
| `result` | 위험 점수, 조사 여부, 판단 기준, 행동 그룹, 모델·정책 버전, 직전 이력과 피처 버전을 담은 JSON |
| `created_at` | DB에 기록한 시각 |

금액은 PostgreSQL `numeric`으로, 평균과 표준편차는 JSON 문자열로 저장해 소수 자릿수를 보존합니다. 원본 시각에는 임의로 시간대를 붙이지 않습니다. 저장 스키마는 `src/finguard/sql/001_scored_transactions.sql`에 있습니다.

별도 PowerShell에서 저장 내용을 확인할 수 있습니다.

```powershell
docker compose exec postgres psql -U finguard -d finguard -c "SELECT transaction_id, amount, result->>'risk_score' AS risk_score, result->>'model_version' AS model_version FROM scored_transactions ORDER BY sequence DESC LIMIT 10;"
```

## 요청 처리 순서와 실패

1. 거래 ID에 DB 잠금을 걸고 이미 저장한 거래인지 확인합니다.
2. 같은 ID·같은 내용이면 모델을 다시 실행하지 않고 저장한 응답을 반환합니다. 모델이 교체되어도 최초 응답을 유지합니다. 같은 ID로 내용을 바꾸면 409입니다.
3. 새 거래라면 카드별 DB 잠금을 걸고 직전 7일 이력을 읽습니다. 동일 카드의 더 이른 거래가 뒤늦게 들어오면 409입니다.
4. 기존 공통 계산기로 직전 이력을 만들고 모델 점수를 계산합니다. 정확히 1시간·7일 전 거래도 포함합니다.
5. 거래와 결과를 함께 저장하고 DB가 최종 저장을 확정한 뒤 200을 반환합니다.

DB 잠금은 여러 API 프로세스 사이에서도 적용됩니다. 같은 카드의 동시 거래는 잠금을 획득한 순서로 처리합니다. 요청 도착 순서를 보장하는 것은 아니며, 먼저 확정된 거래보다 시각이 이르면 거부합니다. DB의 거래 ID 고유 제약도 중복 저장을 막습니다.

모델 계산, INSERT, 최종 COMMIT 중 실패하면 기록 전체를 취소합니다. 메모리 이력을 별도로 수정하지 않으므로 실패한 거래는 다음 계산에 들어가지 않습니다. DB 장애는 503, 모델 계산 실패도 503입니다. 실패 상세 연결 정보는 응답에 노출하지 않습니다. 잠금 대기는 10초, SQL 실행은 30초로 제한합니다.

서버가 저장 확정 직후 응답을 보내기 전에 끊겨도 같은 ID로 재시도하면 이미 저장된 결과를 반환합니다. 결과가 저장되었는지 애매할 때도 새 ID를 만들지 않고 같은 ID와 내용으로 재시도합니다.

## 검증과 다음 단계

통합 테스트는 `TEST_DATABASE_URL`이 가리키는 DB 안에 매번 별도 스키마를 만들고 사용 후 삭제합니다. 기존 개발 테이블은 변경하지 않습니다. 테스트 계정에는 스키마 생성 권한이 필요합니다.

```powershell
$env:TEST_DATABASE_URL = 'postgresql://finguard:finguard_local@127.0.0.1:5432/finguard'
uv run --locked --group api pytest -q -W error
```

DB 주소가 없으면 PostgreSQL 통합 테스트는 건너뜁니다. GitHub Actions에서는 PostgreSQL 17을 실행해 해당 테스트도 수행합니다. 재시작, 모델 교체 후 중복 응답, 동시 중복·동일 카드 요청, 다른 카드의 거래 ID 충돌, DB 연결·모델·INSERT·COMMIT 실패, 이력 시간 경계와 소수 정밀도를 확인합니다.

PostgreSQL 저장 단계에서 전체 테스트 26개를 통과했습니다. 이후 로컬 Docker의 PostgreSQL·Redis를 연결해 전체 테스트 44개를 통과했고 Compose 설정과 두 컨테이너의 정상 실행도 확인했습니다. 실제 저장 모델과 Uvicorn으로 DB·Redis 모드 거래 4건의 점수·이력, 재시작 후 최초 응답 재사용과 캐시 복구도 확인했습니다.

`REDIS_URL`이 없으면 요청마다 DB에서 최근 거래를 읽어 이력을 계산합니다. 설정하면 DB 번호와 일치하는 캐시를 사용합니다. 복구는 PostgreSQL 기록을 기준으로 하며 DB와 Redis가 동시에 저장된다고 가정하지 않습니다. 성능 측정과 사건 생성 시 중복 방지는 후속 작업입니다.
