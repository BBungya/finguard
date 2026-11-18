# 카드 거래 데이터 카드

확인일은 2026-11-14(KST)입니다. 교육용 CSV는 스키마 검증과 거래 재생 점검에 사용합니다. 탐지 모델 평가는 사기 거래가 포함된 별도 데이터로 진행하고, 공개 시연에는 FinGuard에서 직접 만든 합성 데이터를 사용합니다. 파일 버전과 해시는 [데이터 매니페스트](../data/manifests/credit_card_transactions.json)에 기록했습니다.

## 출처와 생성 방식

| 자료 | 확인한 근거 |
| --- | --- |
| [교육용 샘플](https://github.com/BBungya/hana_power_on/blob/1aceec3710af65e5edd86ec7fc7034346de2a491/day4/data/credit_card_transactions-1000.csv) | 파일명과 달리 거래 998건입니다. 같은 커밋에 [전체 CSV의 분할 압축](https://github.com/BBungya/hana_power_on/tree/1aceec3710af65e5edd86ec7fc7034346de2a491/data)이 있습니다. |
| [Priyam Choksi의 Kaggle 배포본](https://www.kaggle.com/datasets/priyamchoksi/credit-card-transactions-dataset) | 버전 1의 `credit_card_transactions.csv`와 교육 저장소 분할 압축의 CSV 앞부분을 각각 비교했습니다. 두 파일 모두 첫 1,000건 안에 샘플 998건이 같은 순서로 있고 24개 컬럼 값이 전부 일치했습니다. 두 파일 모두 샘플에 없는 정상 라벨 행이 2건 있었습니다. 두 행이 빠진 이유와 전체 파일 간 동일성은 확인되지 않았습니다. |
| [Kartik Shenoy의 Kaggle 배포본](https://www.kaggle.com/datasets/kartik2112/fraud-detection) | 게시자는 2019~2020년 데이터를 [Sparkov](https://github.com/namebrandon/Sparkov_Data_Generation)로 생성했다고 설명합니다. 버전 1의 `fraudTrain.csv` 앞부분에서 같은 거래 ID 998개와 같은 라벨을 확인했습니다. 일부 좌표의 문자열 표현이 다르고 `merch_zipcode`는 없었습니다. 거래 일치로 보아 교육 샘플은 이 합성 데이터 계열로 판단됩니다. `merch_zipcode`가 추가된 과정과 배포본 간 가공 경로는 확인되지 않았습니다. |

비교에는 공개 배포 파일의 앞부분을 사용했습니다. `trans_num`으로 거래를 대응시킨 다음 헤더, 셀 값, 행 순서를 비교했습니다. 개별 거래 값은 공개 기록에 포함하지 않습니다.

## 이용 및 공개 조건

- Priyam Choksi 배포본 버전 1은 Kaggle에 Apache 2.0으로 표시됩니다. 이 배포본을 재배포하는 경우 라이선스 사본 제공, 관련 고지 유지, 변경 파일 표시 등 해당 조건을 따릅니다. [Kaggle 메타데이터](https://www.kaggle.com/api/v1/datasets/view/priyamchoksi/credit-card-transactions-dataset) · [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- Kartik Shenoy 배포본 버전 1은 Kaggle에 CC0로 표시됩니다. 이 배포본을 합성 거래 평가에 사용합니다. [Kaggle 메타데이터](https://www.kaggle.com/api/v1/datasets/view/kartik2112/fraud-detection) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
- 교육 저장소에서는 별도 저장소 라이선스 표시를 확인하지 못했습니다. 위 라이선스는 각 Kaggle 배포본에 표시된 조건입니다. FinGuard 공개 저장소에는 데이터 출처, 파일 해시, 집계 통계만 기록합니다. [교육 저장소](https://github.com/BBungya/hana_power_on)

## 샘플 품질과 라벨

| 항목 | 샘플에서 확인한 결과 |
| --- | --- |
| 규모 | 998행, 24컬럼, 고유 카드 식별자 559개 |
| 기간 | 2019-01-01 00:00:18~12:39:27, 하루, 시각 오름차순. `trans_date_trans_time`에는 시간대 표기가 없습니다. |
| 라벨 | 거래 1건당 `is_fraud` 값 1개. `0`은 정상, `1`은 사기로 생성한 거래입니다. 샘플은 정상 998건, 사기 0건(0%)입니다. |
| 중복 | 전체 컬럼 값이 같은 행 0건, 중복 `trans_num` 0건 |
| 결측 | `merch_zipcode`만 빈 값 155건(15.53%). 빈 문자열과 공백만 있는 셀을 결측으로 계산했습니다. |
| 금액과 통화 | `amt`의 관측 범위는 1.03~1,636.87입니다. 미국 주소 형식이 확인되며, 샘플에는 통화 컬럼이나 단위 선언이 없습니다. 원본 통화는 미확인으로 기록합니다. |
| 위치 | Sparkov에서 `lat`·`long`은 고객 주소 좌표이며 `merch_lat`·`merch_long`은 고객 위치 주변에서 생성한 가맹점 좌표입니다. 두 좌표 간 거리는 고객의 실시간 이동을 나타내지 않습니다. 좌표 4개 컬럼의 범위 오류는 0건입니다. |

라벨과 위치의 해석은 생성기 코드에 근거합니다. `Unnamed: 0`은 행 인덱스이며, 중복 검사에는 거래 식별자 `trans_num`을 사용합니다. `cc_num`, `zip`, `merch_zipcode`는 식별자나 코드이므로 원본을 읽을 때 문자열로 보존합니다. 거래 재생 시에는 시간대 적용 여부와 두 시간 컬럼의 정합성을 먼저 확인합니다. [Sparkov 거래 생성 코드](https://github.com/namebrandon/Sparkov_Data_Generation/blob/b5eb45c89d36f2aa4ef16044a42945bed8b96d93/datagen_transaction.py)

샘플에는 사기 거래가 없어 사기 탐지 재현율을 계산할 수 없습니다. 평가에는 정상·사기 거래가 모두 포함된 기간별 분할을 사용하고, 분할마다 거래 수와 사기 건수를 보고합니다.

## 평가용 배포본 확보

2026-11-18에 Kaggle에서 버전 1을 받아 로컬 `data/raw/kaggle/kartik2112/fraud-detection/v1/`에 저장했습니다. `fraudTrain.csv`와 `fraudTest.csv`에서 거래 검증에 필요한 컬럼 및 정상·사기 라벨이 모두 있는 것을 확인했습니다. 파일 크기와 SHA-256은 [평가용 데이터 매니페스트](../data/manifests/sparkov_evaluation.json)에 기록했습니다.

다시 확보할 때는 매니페스트의 다운로드 주소에서 ZIP을 받고, 두 CSV를 풀어 각각의 SHA-256을 확인합니다. 파일 이름은 Kaggle 배포 당시의 구분입니다. FinGuard의 학습·검증·최종 테스트 기간과 사기 건수는 [ML 시간 분할 보고서](../reports/ml_split_distribution.md)에 정리했습니다.

## 공개 데모 식별자와 제외 항목

- 공개 데모는 자체 생성 거래를 사용합니다. 동일 카드의 거래에는 같은 `demo_card_0001` 형식의 카드 ID를 부여하고, 거래마다 별도의 `demo_tx_000001` 형식의 거래 ID를 부여합니다.
- 이름, 상세 주소, 생년월일, 성별, 직업, 우편번호, 정밀 좌표는 공개 데모에서 제외합니다. 화면에는 합성 시각, 금액·통화, 가맹점 업종과 필요한 경우 시·도 수준의 합성 지역만 표시합니다.
- 외부 데이터를 로컬에서 재생할 때 화면에 식별자가 필요하면 원본 `cc_num`과 `trans_num`을 각각 로컬에서만 사용하는 임의 ID로 매핑합니다. 원본 값과 매핑표는 공개·커밋 대상에서 제외합니다.
