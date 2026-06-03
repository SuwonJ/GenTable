from __future__ import annotations

import re
from dataclasses import dataclass
@dataclass(frozen=True)
class AcademicTarget:
    raw: str
    grades: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    excluded_departments: tuple[str, ...] = ()
    special_population_only: bool = False
    open_to_all: bool = False

    def is_eligible(self, grade: str | None, department: str | None) -> bool:
        # 특수 대상 전용 강의는 일반 프로필 후보에서 제외한다.
        if self.special_population_only:
            return False

        if department is not None:
            from src.ingestion import normalize_department_name

            # 화면에서 들어온 학과 이름도 원문 파싱 결과와 같은 별칭으로 맞춘다.
            department = normalize_department_name(department)
        
        # 학년 제한이 있으면 정규화된 학년 이름으로 비교한다.
        if grade and self.grades:
            from src.filters import normalize_target_grade
            normalized_grade = normalize_target_grade(grade)
            if "전체학년" not in self.raw and normalized_grade not in self.grades:
                # 추출 결과가 부족한 경우 원문 포함 여부로 한 번 더 확인한다.
                if normalized_grade not in self.raw:
                    return False

        # 학과 제외 조건을 먼저 적용한 뒤 허용 학과를 검사한다.
        if department:
            if self.excluded_departments and department in self.excluded_departments:
                return False
            # 전체 대상이 아니면서 허용 학과가 있으면 그 목록 안에 있어야 한다.
            if not self.open_to_all and self.departments and department not in self.departments:
                return False
        
        return True

    @classmethod
    def from_raw(cls, raw: str, target_grades: list[str] | None = None) -> AcademicTarget:
        raw_text = str(raw).strip()
        
        # 필터 모듈의 추출 함수를 재사용해 수강대상 해석 기준을 맞춘다.
        from src.filters import (
            extract_excluded_departments,
            extract_target_departments,
            is_open_department_target,
            is_special_population_only,
            normalize_target_grades
        )
        from src.ingestion import normalize_department_name

        grades = tuple(normalize_target_grades(target_grades)) if target_grades else ()
        if not grades and "전체학년" not in raw_text:
            # 로더가 학년 목록을 넘기지 못한 경우 원문에서 직접 추출한다.
            grades = tuple(normalize_target_grades(re.findall(r"([1-4])학년", raw_text)))

        dept_set = extract_target_departments(raw_text)
        excl_set = extract_excluded_departments(raw_text)

        # 정렬된 튜플로 저장해 같은 원문은 항상 같은 객체 값이 되도록 한다.
        return cls(
            raw=raw_text,
            grades=grades,
            departments=tuple(sorted(normalize_department_name(d) for d in dept_set)),
            excluded_departments=tuple(sorted(normalize_department_name(d) for d in excl_set)),
            special_population_only=is_special_population_only(raw_text),
            open_to_all=is_open_department_target(raw_text)
        )



def normalize_wildcard(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "전체":
        # 전체 선택은 실제 제약에서는 제한 없음으로 처리한다.
        return None
    return text
