# 제출용 파일 구조

```text
aitimetable/
├── app.py
├── requirements.txt
├── aitimetable_config.json
├── aitimetable_config2.json
├── sourcedata/
│   ├── export20260323162938.xlsx
│   ├── export20260323162953.xlsx
│   ├── export20260323163001.xlsx
│   ├── export20260323163010.xlsx
│   ├── export20260323163018.xlsx
│   ├── export20260323163025.xlsx
│   ├── kyosun.xlsx
│   └── t2.xlsx
├── src/
│   ├── __init__.py
│   ├── constraints.py
│   ├── data_loader.py
│   ├── engine.py
│   ├── filters.py
│   ├── ingestion.py
│   ├── catalog/
│   │   ├── __init__.py
│   │   └── catalog.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── academic.py
│   │   └── models.py
│   ├── presentation/
│   │   ├── __init__.py
│   │   ├── dataframe_exporter.py
│   │   └── ui_state.py
│   └── services/
│       ├── __init__.py
│       ├── filler_service.py
│       └── scheduler_service.py
├── tests/
│   ├── test_public_api_contract.py
│   └── test_scheduler_filters.py
└── docs/
    ├── README.md
    ├── LEARNING_PATH.md
    ├── all-functions.md
    ├── data-flow.md
    ├── file-structure.md
    ├── function-mapping.md
    ├── product-structure.md
    └── submission-file-structure.md
```

## 구조 구분

| 구분 | 파일 또는 폴더 |
| :--- | :--- |
| 실행 진입점 | `app.py` |
| 의존성 | `requirements.txt` |
| 설정 예시 | `aitimetable_config.json`, `aitimetable_config2.json` |
| 원본 데이터 | `sourcedata/` |
| 핵심 소스 | `src/` |
| 조회 계층 | `src/catalog/` |
| 도메인 계층 | `src/domain/` |
| 화면 보조 계층 | `src/presentation/` |
| 서비스 계층 | `src/services/` |
| 테스트 | `tests/` |
| 문서 | `docs/` |

## 제출 제외 권장 항목

```text
__pycache__/
.venv/
.ipynb_checkpoints/
.idea/
.agents/
.codex
```
