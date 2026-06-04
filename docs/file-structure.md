# 프로젝트 파일 구조 (현재 코드 기준)

이 문서는 **지금 저장소에 존재하는 파일 기준**으로 구조와 책임을 정리한 문서입니다.

## 1. 최상위 구조

```text
/
├── app.py
├── src/
│   ├── services/scheduler_service.py
│   ├── engine.py
│   ├── constraints.py
│   ├── filters.py
│   ├── data_loader.py
│   ├── ingestion.py
│   ├── services/filler_service.py
│   ├── domain/
│   │   ├── models.py
│   │   └── academic.py
│   ├── catalog/catalog.py
│   └── presentation/
│       ├── dataframe_exporter.py
│       └── ui_state.py
├── docs/
└── tests/
```

## 2. 레이어별 역할

| 레이어 | 파일 | 역할 |
| :--- | :--- | :--- |
| UI | `app.py` | Streamlit 입력 수집, 서비스 호출, 탭/화면 배치 |
| UI State/Presentation | `src/presentation/ui_state.py` | 세션 상태/버킷 조작, 검색 어댑터, 반복 렌더 보조 |
| Service (Core Logic) | `src/services/scheduler_service.py`, `src/services/filler_service.py` | 생성/대체추천 파이프라인 조율 및 로직 수행 |
| Engine | `src/engine.py` | `ScheduleRequest`, 백트래킹 탐색, Top-N 관리, 탐색 통계, 점수 계산 |
| Constraints | `src/constraints.py` | 생성 hard 제약 정의 및 `ConstraintRegistry` 조합 |
| Filter Utils | `src/filters.py` | 검색/타겟/정규식 필터와 검색 점수 계산 |
| Ingestion | `src/data_loader.py`, `src/ingestion.py` | 파일 로딩, 강의 정규화, 커리큘럼 필수 과목 추출 |
| Domain | `src/domain/*.py` | `Lecture`, `Schedule`, `StudentProfile`, `AcademicTarget` 모델 |
| Catalog/Presentation | `src/catalog`, `src/presentation` | 엔진 조회 인덱스(`LectureCatalog`)와 DataFrame 변환(`timetable_to_frame`) |

## 3. 최근 리팩토링 반영 규칙

2. 검색 규칙은 `src.filters`, 생성 제약은 `src.constraints`, 점수 계산은 `src.engine.score_candidate`에서 관리합니다.
3. UI 상태/버킷 조작은 `src.presentation.ui_state`, 화면 배치는 `app.py`에 둡니다.
4. Legacy dict → domain 변환과 `time_mask` 같은 파생 필드는 ingestion/service 경계에서 처리합니다.
