# 개발 작업과 GitHub 운영 규칙

최종 수정: 2026-10-31 (KST)

2026-10-31 공개 저장소 BBungya/finguard에 문서·라벨·이슈 24개와 템플릿을 게시했다. 구현·학습·배포는 아직 수행하지 않았다.

## 작업을 진행하는 순서

1. [개발 이슈](DEVELOPMENT_ISSUES.md)에서 선행 작업과 완료 조건을 확인한다.
2. `feat/fg-09-transaction-api`, `fix/fg-09-duplicate-event`, `docs/fg-20-demo`처럼 작업 ID가 드러나는 브랜치를 만든다.
3. 하나의 목적에 필요한 변경과 검증을 묶어 커밋한다. 예: `feat: add transaction replay`, `fix: prevent duplicate state updates`.
4. PR에 문제·변경 이유·검증 명령과 결과·남은 한계를 적고 실제 GitHub 이슈를 연결한다.
5. 완료 조건과 산출물을 확인한 뒤 병합하고 이슈에 결과를 기록한다. 개인 개발도 PR로 설계와 검증 이력을 남긴다. 동료 검토를 받지 않았다면 받았다고 표현하지 않는다.

기본 브랜치는 `main`으로 계획한다. 별도 `dev` 브랜치는 필요가 생길 때 추가한다. 템플릿은 기본 브랜치에 들어간 뒤 GitHub에서 적용 여부를 확인한다.

## 이슈의 공통 구조

목적 → 할 일 → 완료 조건 → 산출물 → 선행 작업 → 작업 결과를 기록한다. 체크박스는 수행한 일만 체크한다. `FG-01`~`FG-24`는 작업 ID다. GitHub 실제 이슈 번호와 URL은 [issue-map.json](issue-map.json)에 기록하며, 선행 작업은 실제 이슈로 연결한다.

한 이슈가 여러 PR로 나뉘면 부분 작업에는 `Refs #실제번호`, 완료 조건 전체를 충족하는 PR에는 `Closes #실제번호`를 사용한다. 게시 전에는 임의의 `#1` 등을 실제 번호처럼 쓰지 않는다.

## 라벨 기준

기본 라벨을 유지하고 작업 분야와 우선순위를 추가한다. 진행 상태는 이슈의 열린/닫힌 상태와 보드로 관리하며 별도 상태 라벨을 중복 추가하지 않는다.

| 구분 | 라벨 | 적용 기준 |
|---|---|---|
| 기본 유형 | `bug` | 기대한 동작과 다른 결함. 개발 계획 전체를 버그로 분류하지 않는다. |
| 기본 유형 | `enhancement` | 신규 기능 또는 기존 기능 개선 |
| 기본 유형 | `documentation` | README·설계·평가·운영 안내 등 문서 작업 |
| 분류·대응 | `question`, `duplicate`, `invalid`, `wontfix` | 추가 정보, 중복, 범위 밖, 진행하지 않을 사유가 있을 때 적용 |
| 참여 | `good first issue`, `help wanted` | 진입 범위가 작고 명확하거나 실제 도움을 구할 때 적용. 모든 작업에 일괄 부착하지 않는다. |
| 분야 | `planning`, `data`, `ml`, `retrieval`, `llm` | 기획·데이터·예측 모델·검색·언어 모델 |
| 분야 | `backend`, `frontend`, `evaluation`, `testing` | API·화면·평가·자동 테스트 |
| 분야 | `devops`, `security`, `performance`, `research` | 운영·보안·성능·추가 실험 |
| 우선순위 | `priority:P0` | 첫 탐지→조사→검증 흐름에 필요한 작업 |
| 우선순위 | `priority:P1` | 비교 실험·자동 검증·배포·문서로 완성하는 작업 |
| 우선순위 | `priority:P2` | 핵심 평가가 끝난 뒤 검토할 선택 확장 |

기존의 `area:*` 라벨은 사용하지 않고 참고 저장소와 같은 짧은 분야명으로 통일한다. 라벨 이름·색상·설명은 [labels.json](../.github/labels.json), 실제 이슈 생성용 초안은 [issue-seed.json](issue-seed.json)을 기준으로 한다. 유형·분야·우선순위는 서로 다른 기준이므로 함께 붙일 수 있다.

## 템플릿

- [개발 작업](../.github/ISSUE_TEMPLATE/development_task.md): 목적, 할 일, 완료 조건, 산출물, 선행 작업, 결과.
- [버그 제보](../.github/ISSUE_TEMPLATE/bug_report.md): 전제·행동·기대 결과·실제 결과, 재현 환경, 마스킹한 로그.
- [기능 제안](../.github/ISSUE_TEMPLATE/feature_request.md): 사용자 문제, 기대 동작, 대안, 범위와 검증 기준.
- [문서·유지보수](../.github/ISSUE_TEMPLATE/maintenance.md): 변경 목적, 영향 범위, 확인 방법.
- [실험·평가](../.github/ISSUE_TEMPLATE/experiment.md): 가설, 기준선, 고정 조건·분할, 지표, 채택 기준, 결과와 한계.
- [PR](../.github/pull_request_template.md): 관련 이슈, 변경 이유, 검증 결과, 데이터·권한 영향, 문서와 남은 한계.

문서만 바꾸는 PR은 링크와 상태 설명을 확인한다. 구현 변경은 영향에 맞는 검증을 기록하고, ML·RAG 실험은 데이터·모델·설정·커밋·실행 환경을 함께 남긴다. 모든 변경에 같은 테스트를 강요하지 않는다.

## 참고한 자료와 적용 범위

- [Semiconductor Docs RAG](https://github.com/BBungya/semiconductor-docs-rag): README 탐색 구조와 이슈의 산출물·선행 작업·결과 기록 방식.
- [GitHub 기본 라벨에 대해 알아보기](https://itpro.tistory.com/207): 기본 유형 라벨과 사용자 정의 라벨의 역할 분리.
- [Issue 및 PR Template](https://soo-develop.tistory.com/43): 반복 작업의 양식을 저장소 파일로 관리하는 접근.
- [GitHub 라벨 문서](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels), [PR 템플릿 문서](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository): 지원 경로와 동작 확인.

블로그의 예제 문안을 그대로 복제하지 않고 FinGuard의 거래 정합성·모델 평가·보고서 검증에 맞게 작성했다. 블로그의 `feat` 대신 GitHub 기본 `enhancement`를 사용한다. 개인 개발 규모에 맞춰 `main` 중심 흐름을 선택했다.
