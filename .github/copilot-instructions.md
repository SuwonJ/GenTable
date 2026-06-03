# Copilot instructions for this repository

## Build, test, and lint commands

```bash
# install dependencies
pip install -r requirements.txt

# run the app
streamlit run app.py

# run all tests
python -m unittest discover -s tests -p "test_*.py"

# run a single test
python -m unittest tests.test_scheduler_filters.SchedulerFilterTests.test_generate_timetable_prefers_later_optional_course
```

No dedicated lint configuration/command is currently defined in this repository.

## High-level architecture

1. **UI + state orchestration (`app.py`)**
   - Streamlit owns workflow/state (`preferred_ids`, `candidate_ids`, `excluded_ids`, `alternative_groups`, `controls`).
   - Search tab filters courses via `src.filters.course_matches_filters`.
   - Results tab calls `src.scheduler.generate_timetables(...)`; replacement suggestions call `recommend_fillers(...)`.

2. **Ingestion and normalization (`src/data_loader.py`)**
   - `process_files()` separates curriculum files (`"교과과정"` in filename) from lecture files.
   - Lecture rows are normalized into a legacy dict schema (`course_id`, `name`, `category`, `target_raw`, `meetings`, `time_mask`, etc.).
   - Curriculum requirements are loaded into grade/semester buckets used later for required-subject selection.

3. **Legacy facade to new engine (`src/scheduler.py` -> `src/services/scheduler_service.py`)**
   - `src/scheduler.py` keeps the external API stable for app/tests.
   - Service layer applies profile-aware filtering, resolves required subject names, converts legacy dict courses into domain `Lecture` objects, and executes the engine.

4. **Domain + constraints + search engine**
   - Domain objects (`src/domain/models.py`) are immutable (`Lecture`, `Schedule`, `StudentProfile`) and carry fast conflict data (`time_mask`).
   - Constraints are assembled in `src/constraints/registry.py` and enforced in `src/engine/backtracking.py` (time conflict, duplicate subject, credit range, required/excluded lectures, alternative groups, student eligibility).
   - Search strategy: choose required-subject sections first, then backtrack optional lectures with pruning (`src/engine/pruning.py`) and keep top-N candidates (`src/engine/optimizer.py`).

5. **Output shape**
   - Engine scoring still uses legacy dict courses (`score_candidate` callback from `src/scheduler.py`), and final candidates are returned in the legacy structure consumed directly by `app.py`.

## Key codebase conventions

- Keep the public API stable for callers: `app.py` and tests call `src.scheduler.generate_timetables(...)`; internals can change behind this facade.
- The repository still uses a **legacy dict course payload** at integration boundaries (UI/tests/scoring). Domain models are used inside the engine pipeline, then converted back for scoring/output.
- Time conflict logic relies on minute-level bitmasks (`time_mask`) for speed. Any new/modified course normalization must preserve `meetings` + `time_mask`.
- Filter/eligibility logic should reuse `src.filters` helpers (especially target-grade/department/special-population parsing), not duplicate regex/parsing rules in new modules.
- Alternative group semantics are: **OR within a group, AND across groups** (`AlternativeGroupConstraint` requires at least one lecture from each group).
- Required basket lectures can override exclusion checks (`ExcludedLectureConstraint` + service-level preferred handling). Preserve this precedence when changing selection logic.
- Grade/semester/department wildcards use `"전체"` as “unset” (`normalize_wildcard` / `StudentProfile.from_legacy`), and grade matching often converts numeric grades to `"N학년"`.
- User-facing generation diagnostics are returned through `info["warnings"]` (aggregated from ingestion + engine); keep warnings informative rather than silently dropping conditions.
