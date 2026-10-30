# FinGuard 개발 작업과 이슈

최종 수정: 2026-10-31 (KST)

상태: GitHub 이슈 24개 게시 완료. FG 작업 ID별 실제 이슈 링크는 아래에 연결했다. 구현은 미착수다.

핵심·완성 작업 20개와 선택 확장 4개로 구성한다. 개별 이슈의 선행 작업을 우선하며, 8주는 일정 가정이다.

| 작업 ID | 작업 | 우선순위 | 계획 시점 |
|---|---|---|---|
| [FG-01](#fg-01) | [기획] 개발 구조·환경·작업 규칙 확정 | P0 | 1주 |
| [FG-02](#fg-02) | [데이터] 거래 데이터 출처·라벨·이용 조건 확인 | P0 | 1주 |
| [FG-03](#fg-03) | [수집] 거래 스키마 검증·시간순 재생 구현 | P0 | 1~2주 |
| [FG-04](#fg-04) | [피처] 과거 이력 계산과 학습·추론 일치 검증 | P0 | 2주 |
| [FG-05](#fg-05) | [평가 데이터] ML 시간 분할과 조사 예산 고정 | P0 | 2주 |
| [FG-06](#fg-06) | [기준선] 규칙·로지스틱 회귀와 탐지 평가 | P0 | 2주 |
| [FG-07](#fg-07) | [모델] 랜덤포레스트·XGBoost와 오류 분석 | P1 | 3주 |
| [FG-08](#fg-08) | [행동 분석] 군집·이상 점수 제거 실험 | P1 | 3주 |
| [FG-09](#fg-09) | [거래 API] 점수·고객 상태·멱등성 구현 | P0 | 4주 |
| [FG-10](#fg-10) | [조사 화면] 사건 상세·보고서 상태·검토 이력 | P0 | 4주 |
| [FG-11](#fg-11) | [문서] 조사 지침 출처·파싱·청킹·버전 관리 | P0 | 5주 |
| [FG-12](#fg-12) | [검색] 키워드·벡터·하이브리드 기준 비교 | P0 | 5주 |
| [FG-13](#fg-13) | [보고서] 구조화 초안·수치·인용 검증 | P0 | 6주 |
| [FG-14](#fg-14) | [에이전트] 제한된 도구·실행 흐름·AI 호출 관리 | P0 | 6주 |
| [FG-15](#fg-15) | [평가] 보고서·에이전트 통합 평가셋과 실행기 | P0 | 6~7주 |
| [FG-16](#fg-16) | [품질] 회귀 테스트와 GitHub Actions | P1 | 7주 |
| [FG-17](#fg-17) | [보안] 사건 권한·개인정보·문서 내 악성 지시 검증 | P0 | 7주 |
| [FG-18](#fg-18) | [운영] Docker·관측·장애·백업 복구 | P1 | 7~8주 |
| [FG-19](#fg-19) | [개선] 실패 분류·가설·한 요소씩 비교 | P1 | 7~8주 |
| [FG-20](#fg-20) | [포트폴리오] README·데모·측정 결과·기여 정리 | P1 | 8주 |
| [FG-21](#fg-21) | [확장·연합학습] 기관별 분할과 협력 효과 실험 | P2 | 핵심 평가 이후 |
| [FG-22](#fg-22) | [확장·AML] 계좌 관계 데이터와 그래프 조사 | P2 | 데이터 확보 이후 |
| [FG-23](#fg-23) | [확장·성능] 대기열·배치·캐시·부하 최적화 | P2 | 핵심 평가 이후 |
| [FG-24](#fg-24) | [확장·뉴스] 금융사기 참고 뉴스 수집·최신성 관리 | P2 | 핵심 평가 이후 |

<a id="fg-01"></a>

## FG-01 [기획] 개발 구조·환경·작업 규칙 확정

라벨: documentation, planning, priority:P0

## 목적

새 환경에서도 개발을 시작할 수 있는 기반을 만든다.

## 할 일

- [ ] Python 버전·의존성 관리와 환경변수 예시 정의
- [ ] src·configs·evals·reports·tests 역할과 구성도 작성
- [ ] 브랜치·PR·설계 결정 기록 방식 적용

## 완료 조건

- [ ] 문서대로 개발 환경 구성 가능
- [ ] 현재 파일과 예정 파일을 구분하고 비밀 키를 포함하지 않음

## 산출물

pyproject.toml, 잠금 파일, .env.example, docs/architecture.md

## 선행 작업

없음. 이 작업부터 시작한다.

## 일정·범위

- 계획 시점: 1주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-01. GitHub 이슈: [#1](https://github.com/BBungya/finguard/issues/1).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-02"></a>

## FG-02 [데이터] 거래 데이터 출처·라벨·이용 조건 확인

라벨: documentation, data, priority:P0

## 목적

평가와 공개에 사용할 수 있는 데이터 범위를 확정한다.

## 할 일

- [ ] 출처·생성 방식·이용 및 재배포 조건 확인
- [ ] 기간·사기 표본·통화·중복·결측·위치 의미 분석
- [ ] 제외할 개인정보와 데모 식별자 정의

## 완료 조건

- [ ] 라벨과 출처·공개 조건을 데이터 카드에 기록
- [ ] 1,000행 샘플을 충분한 평가 데이터라고 가정하지 않음

## 산출물

data/manifests, docs/data_card.md

## 선행 작업

- [#1 — FG-01](https://github.com/BBungya/finguard/issues/1)

## 일정·범위

- 계획 시점: 1주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-02. GitHub 이슈: [#2](https://github.com/BBungya/finguard/issues/2).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-03"></a>

## FG-03 [수집] 거래 스키마 검증·시간순 재생 구현

라벨: enhancement, data, backend, priority:P0

## 목적

같은 입력을 같은 순서로 재현할 수 있게 한다.

## 할 일

- [ ] 거래 ID·시간·금액·필수 필드 검증
- [ ] 안정적인 시간순 정렬·동시각 순서·재생 속도 설정
- [ ] 중복·잘못된 입력·늦게 도착한 거래 처리 정책 정의

## 완료 조건

- [ ] 입력 통계와 실패 원인·재생 설정 기록
- [ ] 동일 입력과 설정으로 동일 순서 재현

## 산출물

거래 스키마, 재생기, 입력 검증 결과

## 선행 작업

- [#2 — FG-02](https://github.com/BBungya/finguard/issues/2)

## 일정·범위

- 계획 시점: 1~2주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-03. GitHub 이슈: [#3](https://github.com/BBungya/finguard/issues/3).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-04"></a>

## FG-04 [피처] 과거 이력 계산과 학습·추론 일치 검증

라벨: enhancement, data, ml, priority:P0

## 목적

거래 당시 알 수 있는 정보로 일관된 피처를 만든다.

## 할 일

- [ ] 거래 직전 고객 이력의 건수·평균·표준편차 계산
- [ ] 초기 고객·결측·윈도 경계·동시각 규칙 통일
- [ ] 공통 계산 함수와 피처 스키마·버전 정의

## 완료 조건

- [ ] 미래 거래 변경이 과거 피처에 영향을 주지 않음
- [ ] 동일 거래열의 오프라인·온라인 계산이 허용 오차 내 일치

## 산출물

피처 계산 모듈, 피처 사전, 일치·누수 검증 결과

## 선행 작업

- [#3 — FG-03](https://github.com/BBungya/finguard/issues/3)

## 일정·범위

- 계획 시점: 2주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-04. GitHub 이슈: [#4](https://github.com/BBungya/finguard/issues/4).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-05"></a>

## FG-05 [평가 데이터] ML 시간 분할과 조사 예산 고정

라벨: enhancement, data, evaluation, priority:P0

## 목적

모델과 임계값을 같은 기준으로 평가한다.

## 할 일

- [ ] 학습·검증·최종 테스트 기간과 신규 고객 정의
- [ ] 분할별 양성 표본·분포 점검
- [ ] 일일 조사 예산 B와 지표·비용 가정 정의

## 완료 조건

- [ ] 임계값·설정 조정과 최종 평가 용도가 분리됨
- [ ] 데이터 버전·기간·분할·평가 계산법이 기록됨

## 산출물

ML 분할 설정, 평가 명세, 분포 보고서

## 선행 작업

- [#2 — FG-02](https://github.com/BBungya/finguard/issues/2)
- [#4 — FG-04](https://github.com/BBungya/finguard/issues/4)

## 일정·범위

- 계획 시점: 2주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-05. GitHub 이슈: [#5](https://github.com/BBungya/finguard/issues/5).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-06"></a>

## FG-06 [기준선] 규칙·로지스틱 회귀와 탐지 평가

라벨: enhancement, ml, evaluation, priority:P0

## 목적

이후 개선을 판단할 재현 가능한 기준선을 확보한다.

## 할 일

- [ ] 규칙과 로지스틱 회귀 구현
- [ ] 학습 구간에서 전처리기 학습
- [ ] AP·혼동행렬·Precision·Recall·Precision@B·Recall@B 계산

## 완료 조건

- [ ] 동일 시간 분할·입력 조건으로 결과 저장
- [ ] 검증 구간에서 고른 임계값으로 최종 평가

## 산출물

기준 모델, 실행 설정, reports/baseline.md

## 선행 작업

- [#4 — FG-04](https://github.com/BBungya/finguard/issues/4)
- [#5 — FG-05](https://github.com/BBungya/finguard/issues/5)

## 일정·범위

- 계획 시점: 2주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-06. GitHub 이슈: [#6](https://github.com/BBungya/finguard/issues/6).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-07"></a>

## FG-07 [모델] 랜덤포레스트·XGBoost와 오류 분석

라벨: enhancement, ml, evaluation, priority:P1

## 목적

복잡한 모델의 추가 효과와 한계를 판단한다.

## 할 일

- [ ] 기준선과 동일 조건에서 후보 학습
- [ ] 신규 고객·시간대·금액별 오류 분석
- [ ] 모델 점수의 보정 수준과 선택 이유 기록

## 완료 조건

- [ ] 실험 설정·seed·버전·환경·재현 명령 보존
- [ ] 모델 복잡도·성능·추론 비용을 함께 비교

## 산출물

후보 모델 설정, 비교 결과, 모델 카드

## 선행 작업

- [#6 — FG-06](https://github.com/BBungya/finguard/issues/6)

## 일정·범위

- 계획 시점: 3주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-07. GitHub 이슈: [#7](https://github.com/BBungya/finguard/issues/7).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-08"></a>

## FG-08 [행동 분석] 군집·이상 점수 제거 실험

라벨: enhancement, ml, research, priority:P1

## 목적

고객 행동 정보가 실제 탐지를 개선하는지 확인한다.

## 할 일

- [ ] 학습 구간에서 스케일러·KMeans·Isolation Forest 학습
- [ ] 군집 특성과 이상 점수 탐색
- [ ] 추가 피처 전후 제거 실험과 고객별 영향 분석

## 완료 조건

- [ ] 군집 번호에 위험 순서를 부여하지 않음
- [ ] 이상치를 확정 사기로 표시하지 않고 채택 근거 제시

## 산출물

군집 분석, 제거 실험, 채택·폐기 기록

## 선행 작업

- [#7 — FG-07](https://github.com/BBungya/finguard/issues/7)

## 일정·범위

- 계획 시점: 3주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-08. GitHub 이슈: [#8](https://github.com/BBungya/finguard/issues/8).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-09"></a>

## FG-09 [거래 API] 점수·고객 상태·멱등성 구현

라벨: enhancement, backend, priority:P0

## 목적

재시도와 동시 요청에도 거래와 고객 상태를 일관되게 관리한다.

## 할 일

- [ ] FastAPI 점수 API와 PostgreSQL 원본 기록
- [ ] Redis 상태·고객별 원자적 갱신·거래 ID 중복 방지
- [ ] 모델·피처·정책 버전 기록 및 상태 복구 설계

## 완료 조건

- [ ] 재전송으로 거래·상태·사건이 중복되지 않음
- [ ] LLM 없이 API가 동작하고 피처 일치가 유지됨

## 산출물

API 명세, 저장 스키마, 통합·동시 요청 검증

## 선행 작업

- [#3 — FG-03](https://github.com/BBungya/finguard/issues/3)
- [#4 — FG-04](https://github.com/BBungya/finguard/issues/4)
- [#6 — FG-06](https://github.com/BBungya/finguard/issues/6)

## 일정·범위

- 계획 시점: 4주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-09. GitHub 이슈: [#9](https://github.com/BBungya/finguard/issues/9).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-10"></a>

## FG-10 [조사 화면] 사건 상세·보고서 상태·검토 이력

라벨: enhancement, backend, frontend, priority:P0

## 목적

담당자가 의심 거래의 근거를 확인하고 조사 결과를 기록한다.

## 할 일

- [ ] Gradio 조사 목록·거래 상세·과거 이력 화면
- [ ] 사용자·사건별 대화와 보고서 상태 모델
- [ ] 담당자 수정·확정 이력 및 모의 처리 표시

## 완료 조건

- [ ] 거래 재생→탐지→사건 선택 흐름 시연
- [ ] 권한 확인 후 저장하고 원본 식별정보를 노출하지 않음

## 산출물

조사 화면, 사건·검토 API, 화면 시나리오

## 선행 작업

- [#9 — FG-09](https://github.com/BBungya/finguard/issues/9)

## 일정·범위

- 계획 시점: 4주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-10. GitHub 이슈: [#10](https://github.com/BBungya/finguard/issues/10).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-11"></a>

## FG-11 [문서] 조사 지침 출처·파싱·청킹·버전 관리

라벨: enhancement, data, retrieval, priority:P0

## 목적

조사 지침을 원문 위치까지 추적 가능한 검색 자료로 만든다.

## 할 일

- [ ] 이용 가능한 문서의 출처·발행일·버전 기록
- [ ] PDF 페이지·본문·표의 수치·조건 검토
- [ ] 모의 지침 표시·청크 ID·원문 근거 구간 저장

## 완료 조건

- [ ] 청크에서 원문·버전·페이지 추적 가능
- [ ] 파싱 오류와 자료별 공개 범위를 문서화

## 산출물

문서 목록, 파서·청커, 파싱 품질 기록

## 선행 작업

- [#1 — FG-01](https://github.com/BBungya/finguard/issues/1)
- [#2 — FG-02](https://github.com/BBungya/finguard/issues/2)

## 일정·범위

- 계획 시점: 5주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-11. GitHub 이슈: [#11](https://github.com/BBungya/finguard/issues/11).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-12"></a>

## FG-12 [검색] 키워드·벡터·하이브리드 기준 비교

라벨: enhancement, retrieval, evaluation, priority:P0

## 목적

금융 용어와 의미가 다른 질문에서 필요한 근거를 찾는다.

## 할 일

- [ ] BM25와 임베딩·Chroma 검색 기준선 구성
- [ ] 동일 질문으로 검색 비교·필요시 RRF 결합 실험
- [ ] 문서·버전·접근 범위 필터와 검색 근거 ID 유지

## 완료 조건

- [ ] 비교에 쓴 정답 문서·페이지와 질문을 기록
- [ ] 검색 방식·top-k·지연과 실패 사례를 재현 가능

## 산출물

검색기, 설정, 검색 기준 비교 결과

## 선행 작업

- [#11 — FG-11](https://github.com/BBungya/finguard/issues/11)

## 일정·범위

- 계획 시점: 5주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-12. GitHub 이슈: [#12](https://github.com/BBungya/finguard/issues/12).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-13"></a>

## FG-13 [보고서] 구조화 초안·수치·인용 검증

라벨: enhancement, llm, backend, priority:P0

## 목적

관측 사실과 문서 근거를 구분한 검토 가능한 초안을 만든다.

## 할 일

- [ ] 관측 사실·모델 설명·지침·확인 사항 스키마
- [ ] 숫자를 조회 결과에 연결하고 실제 인용 ID 대조
- [ ] 초안·검증 실패·검토 대기·확정 상태 전이 정의

## 완료 조건

- [ ] 잘못된 금액·가짜 인용이 검증 실패로 표시됨
- [ ] 필수 검증 실패와 AI의 직접 확정 요청을 차단

## 산출물

보고서 스키마, 검증기, 실패·정상 예시

## 선행 작업

- [#9 — FG-09](https://github.com/BBungya/finguard/issues/9)
- [#10 — FG-10](https://github.com/BBungya/finguard/issues/10)
- [#12 — FG-12](https://github.com/BBungya/finguard/issues/12)

## 일정·범위

- 계획 시점: 6주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-13. GitHub 이슈: [#13](https://github.com/BBungya/finguard/issues/13).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-14"></a>

## FG-14 [에이전트] 제한된 도구·실행 흐름·AI 호출 관리

라벨: enhancement, llm, backend, priority:P0

## 목적

허용된 사건의 근거를 수집하고 검증된 초안을 담당자에게 전달한다.

## 할 일

- [ ] LangGraph와 사건 조회·통계·검색 도구 연결
- [ ] 서버 권한 확인·호출 수·시간·토큰 예산 제한
- [ ] 공통 AI 호출 모듈의 필드 제한·마스킹·실패 처리

## 완료 조건

- [ ] 도구 입력·결과 참조와 모델·프롬프트 버전 추적
- [ ] 타임아웃·반복 호출이 종료되며 점수 API는 계속 동작

## 산출물

에이전트, 도구 명세, 실행·실패 기록

## 선행 작업

- [#13 — FG-13](https://github.com/BBungya/finguard/issues/13)

## 일정·범위

- 계획 시점: 6주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-14. GitHub 이슈: [#14](https://github.com/BBungya/finguard/issues/14).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-15"></a>

## FG-15 [평가] 보고서·에이전트 통합 평가셋과 실행기

라벨: enhancement, evaluation, llm, priority:P0

## 목적

검색·생성·도구 선택 실패를 분리해 측정한다.

## 할 일

- [ ] 단일·복수 근거·답 없음·잘못된 전제 질문과 정답 작성
- [ ] 개발·검증·최종 평가 질문과 유사 질문 분리
- [ ] LLM만·기본 RAG·도구 흐름의 품질·지연·비용 비교

## 완료 조건

- [ ] 질문마다 근거·답변 가능성·검토 상태 기록
- [ ] 수치·인용 정확성·답변 유보·라우팅을 분모와 함께 보고

## 산출물

evals 데이터·스키마, 평가 실행기, 결과 보고서

## 선행 작업

- [#5 — FG-05](https://github.com/BBungya/finguard/issues/5)
- [#11 — FG-11](https://github.com/BBungya/finguard/issues/11)
- [#13 — FG-13](https://github.com/BBungya/finguard/issues/13)
- [#14 — FG-14](https://github.com/BBungya/finguard/issues/14)

## 일정·범위

- 계획 시점: 6~7주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-15. GitHub 이슈: [#15](https://github.com/BBungya/finguard/issues/15).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-16"></a>

## FG-16 [품질] 회귀 테스트와 GitHub Actions

라벨: enhancement, testing, devops, priority:P1

## 목적

거래·출처·보고서 동작이 변경으로 깨지는지 자동 확인한다.

## 할 일

- [ ] 직접 만든 소형 입력으로 피처·중복·상태 전이 시험
- [ ] 가짜 인용·도구 실패·오프라인·온라인 차이 회귀 시험
- [ ] PR의 코드 검사·핵심 테스트와 실제 모델 평가 분리

## 완료 조건

- [ ] 고정 입력 테스트가 핵심 오류를 탐지
- [ ] 비용 있는 모델 평가는 수동 실행하고 키·로그를 보호

## 산출물

tests, .github/workflows, CI 실행 안내

## 선행 작업

- [#9 — FG-09](https://github.com/BBungya/finguard/issues/9)
- [#13 — FG-13](https://github.com/BBungya/finguard/issues/13)
- [#14 — FG-14](https://github.com/BBungya/finguard/issues/14)

## 일정·범위

- 계획 시점: 7주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-16. GitHub 이슈: [#16](https://github.com/BBungya/finguard/issues/16).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-17"></a>

## FG-17 [보안] 사건 권한·개인정보·문서 내 악성 지시 검증

라벨: enhancement, security, backend, testing, priority:P0

## 목적

조회·대화·근거·보고서 경로의 권한 경계를 검증한다.

## 할 일

- [ ] 다른 담당자 사건 ID·대화 혼입·출처 경로 시험
- [ ] 문서 속 악성 지시·임의 통계 인자·상태 변경 시험
- [ ] 외부 전송 요청을 모의 수집해 식별정보 노출 확인

## 완료 조건

- [ ] 시도·실패 수와 정상 입력 오탐률 기록
- [ ] 서버 권한·도구 제한·담당자 확정 제약을 실제 시험

## 산출물

위협 모델, 보안 시나리오, 마스킹·접근 결과

## 선행 작업

- [#10 — FG-10](https://github.com/BBungya/finguard/issues/10)
- [#14 — FG-14](https://github.com/BBungya/finguard/issues/14)

## 일정·범위

- 계획 시점: 7주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-17. GitHub 이슈: [#17](https://github.com/BBungya/finguard/issues/17).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-18"></a>

## FG-18 [운영] Docker·관측·장애·백업 복구

라벨: enhancement, devops, backend, priority:P1

## 목적

새 환경 실행과 서비스 상태·데이터 복구를 확인한다.

## 할 일

- [ ] API·화면·DB·Redis의 Compose와 영구 저장
- [ ] Redis·LLM 장애·재시작·늦은 거래 시나리오
- [ ] DB 백업 복구·모델 및 설정 롤백·요청 지연 관측

## 완료 조건

- [ ] 문서대로 실행하고 실제 백업 복구를 수행
- [ ] 탐지·보고서 장애를 구분하고 환경·부하 조건 기록

## 산출물

Compose, 운영 안내, 장애·복구·기초 부하 결과

## 선행 작업

- [#10 — FG-10](https://github.com/BBungya/finguard/issues/10)
- [#14 — FG-14](https://github.com/BBungya/finguard/issues/14)
- [#16 — FG-16](https://github.com/BBungya/finguard/issues/16)
- [#17 — FG-17](https://github.com/BBungya/finguard/issues/17)

## 일정·범위

- 계획 시점: 7~8주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-18. GitHub 이슈: [#18](https://github.com/BBungya/finguard/issues/18).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-19"></a>

## FG-19 [개선] 실패 분류·가설·한 요소씩 비교

라벨: enhancement, evaluation, research, priority:P1

## 목적

실패 원인에 맞는 변경의 효과를 확인한다.

## 할 일

- [ ] 누수·오탐·피처 차이·파싱·검색·생성 실패 분류
- [ ] 한 번에 변경할 요소와 채택 기준 정의
- [ ] 고정 검증셋에서 전후 비교 후 최종 평가 실행

## 완료 조건

- [ ] 최종 테스트셋을 개선 반복에 사용하지 않음
- [ ] 효과 없는 변경도 원인·비용·판단과 함께 기록

## 산출물

실패 사례집, 비교 실험 보고서, 설계 결정

## 선행 작업

- [#7 — FG-07](https://github.com/BBungya/finguard/issues/7)
- [#8 — FG-08](https://github.com/BBungya/finguard/issues/8)
- [#15 — FG-15](https://github.com/BBungya/finguard/issues/15)

## 일정·범위

- 계획 시점: 7~8주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-19. GitHub 이슈: [#19](https://github.com/BBungya/finguard/issues/19).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-20"></a>

## FG-20 [포트폴리오] README·데모·측정 결과·기여 정리

라벨: documentation, documentation, priority:P1

## 목적

처음 보는 사람이 구현과 검증 근거를 따라가게 한다.

## 할 일

- [ ] 실제 실행·화면·지표·한계·기여로 README 갱신
- [ ] 탐지→조사→오류 검증→담당자 검토 3분 시연
- [ ] 기술 선택·폐기 대안·참고 코드·AI 사용 구분

## 완료 조건

- [ ] 실행 가능한 링크 또는 재현 절차와 결과 연결
- [ ] 구현 전 기능·미측정 수치를 성과로 표시하지 않음

## 산출물

README, 시연 영상, 실험·설계 문서, 소개 문장

## 선행 작업

- [#18 — FG-18](https://github.com/BBungya/finguard/issues/18)
- [#19 — FG-19](https://github.com/BBungya/finguard/issues/19)

## 일정·범위

- 계획 시점: 8주. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-20. GitHub 이슈: [#20](https://github.com/BBungya/finguard/issues/20).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-21"></a>

## FG-21 [확장·연합학습] 기관별 분할과 협력 효과 실험

라벨: enhancement, ml, research, priority:P2

## 목적

원본 데이터 공유 없이 협력할 때의 효과와 한계를 탐색한다.

## 할 일

- [ ] 기관별 차이를 모사할 분할과 가정 정의
- [ ] 개별·중앙 집중·연합 학습 조건 비교
- [ ] 통신·모델·개인정보 위험과 보완 범위 기록

## 완료 조건

- [ ] 동일한 독립 평가 조건으로 비교
- [ ] 모의 실험을 실제 은행 간 공동모델 성과로 표현하지 않음

## 산출물

기관 분할 명세, 비교 결과, 한계 보고서

## 선행 작업

- [#19 — FG-19](https://github.com/BBungya/finguard/issues/19)

## 일정·범위

- 계획 시점: 핵심 평가 이후. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-21. GitHub 이슈: [#21](https://github.com/BBungya/finguard/issues/21).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-22"></a>

## FG-22 [확장·AML] 계좌 관계 데이터와 그래프 조사

라벨: enhancement, data, ml, research, priority:P2

## 목적

계좌 간 자금 흐름을 별도 업무 문제로 평가한다.

## 할 일

- [ ] 송금 관계·업무 라벨·공개 조건이 있는 데이터 확보
- [ ] 관계·시간·경로 피처와 조사 근거 설계
- [ ] 단순 규칙과 그래프 방식의 분리된 평가

## 완료 조건

- [ ] 필요 데이터 미확보 시 구현을 시작하지 않음
- [ ] 카드 사기 지표를 보이스피싱·AML 성능으로 사용하지 않음

## 산출물

별도 데이터 카드, 그래프 설계, AML 평가

## 선행 작업

- [#2 — FG-02](https://github.com/BBungya/finguard/issues/2)
- [#19 — FG-19](https://github.com/BBungya/finguard/issues/19)

## 일정·범위

- 계획 시점: 데이터 확보 이후. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-22. GitHub 이슈: [#22](https://github.com/BBungya/finguard/issues/22).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-23"></a>

## FG-23 [확장·성능] 대기열·배치·캐시·부하 최적화

라벨: enhancement, performance, devops, research, priority:P2

## 목적

권한과 최신성을 유지하면서 지연·비용을 줄인다.

## 할 일

- [ ] 단계별 병목·자원·실제 사용량 측정
- [ ] 제한된 동시 처리·취소·재시도·대기열 설계
- [ ] 권한·사건·문서·모델 버전을 반영한 캐시와 무효화

## 완료 조건

- [ ] 고정 부하에서 전후 지연·오류·비용 비교
- [ ] 캐시로 다른 사건·이전 문서 정보가 노출되지 않음

## 산출물

부하 시나리오, 최적화 비교, 운영 한도

## 선행 작업

- [#17 — FG-17](https://github.com/BBungya/finguard/issues/17)
- [#18 — FG-18](https://github.com/BBungya/finguard/issues/18)
- [#19 — FG-19](https://github.com/BBungya/finguard/issues/19)

## 일정·범위

- 계획 시점: 핵심 평가 이후. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-23. GitHub 이슈: [#23](https://github.com/BBungya/finguard/issues/23).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.


<a id="fg-24"></a>

## FG-24 [확장·뉴스] 금융사기 참고 뉴스 수집·최신성 관리

라벨: enhancement, data, retrieval, research, priority:P2

## 목적

최근 사기 동향을 조사 참고 자료로 별도 제공한다.

## 할 일

- [ ] RSS·원문 URL·발행일·수집일·이용 범위 기록
- [ ] 중복·변경 감지와 참고 뉴스 탭
- [ ] 지침·뉴스를 구분하고 사건 시점과 자료 시점 표시

## 완료 조건

- [ ] 뉴스를 사기 확정 근거나 과거 모델 입력으로 섞지 않음
- [ ] 삭제·수정·접근 불가 자료의 동작과 출처 확인

## 산출물

수집기, 출처 목록, 뉴스 탭, 갱신 검증

## 선행 작업

- [#11 — FG-11](https://github.com/BBungya/finguard/issues/11)
- [#12 — FG-12](https://github.com/BBungya/finguard/issues/12)
- [#18 — FG-18](https://github.com/BBungya/finguard/issues/18)

## 일정·범위

- 계획 시점: 핵심 평가 이후. 8주는 가정이며 확정 마감일이 아니다.
- 작업 ID: FG-24. GitHub 이슈: [#24](https://github.com/BBungya/finguard/issues/24).
- 상세 요구사항: [프로젝트 기획서](https://github.com/BBungya/finguard/blob/main/docs/PROJECT_PLAN.md).

## 작업 결과

작업 후 관련 PR·실행 결과·남은 문제를 기록한다. 현재는 미착수이며, 산출물 경로도 예정 사항이다.

