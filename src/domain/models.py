from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from src.domain.academic import AcademicTarget, normalize_wildcard

DAY_ORDER = ["월", "화", "수", "목", "금"]
DAY_MAP = {day: i for i, day in enumerate(DAY_ORDER)}


class CourseCategory(StrEnum):
    MAJOR_REQUIRED = "major_required"
    MAJOR_ELECTIVE = "major_elective"
    GENERAL_REQUIRED = "general_required"
    GENERAL_ELECTIVE = "general_elective"
    OTHER = "other"


@dataclass(frozen=True)
class TimeSlot:
    day: str
    start_minute: int
    end_minute: int
    location: str = ""

    def overlaps(self, other: "TimeSlot") -> bool:
        # 같은 요일에서 시간 구간이 서로 걸치면 충돌로 본다.
        return self.day == other.day and self.start_minute < other.end_minute and other.start_minute < self.end_minute


@dataclass(frozen=True)
class Subject:
    code: str
    name: str
    category: CourseCategory | str
    credits: float
    area: str = ""


@dataclass(frozen=True)
class Lecture:
    id: str
    subject: Subject
    professor: str
    seats: int
    target_raw: str
    target: AcademicTarget
    time_slots: tuple[TimeSlot, ...]
    source: str = ""
    raw: Mapping[str, object] = field(default_factory=dict, compare=False, repr=False)

    @property
    def time_mask(self) -> int:
        value = self.raw.get("time_mask", 0)
        # 로더가 만들어 둔 마스크가 없으면 안전하게 0으로 처리한다.
        return int(value) if isinstance(value, int) else 0


@dataclass(frozen=True)
class StudentProfile:
    grade: str | None = None
    semester: str | None = None
    department: str | None = None
    major: str | None = None
    track: str | None = None

    @classmethod
    def from_legacy(
        cls,
        grade: str | None = None,
        semester: str | None = None,
        departments: list[str] | tuple[str, ...] | None = None,
    ) -> "StudentProfile":
        department = departments[0] if departments else None
        # 화면의 전체/빈 값은 제약 없음으로 정규화한다.
        return cls(
            grade=normalize_wildcard(grade),
            semester=normalize_wildcard(semester),
            department=normalize_wildcard(department),
        )


@dataclass(frozen=True)
class Schedule:
    lectures: tuple[Lecture, ...] = ()
    _credits: float = field(init=False, repr=False)
    _lecture_ids: frozenset[str] = field(init=False, repr=False)
    _subject_names: frozenset[str] = field(init=False, repr=False)
    _time_mask: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # 불변 데이터 클래스라 계산 필드는 강제 대입으로 초기화한다.
        object.__setattr__(self, "_credits", sum(lecture.subject.credits for lecture in self.lectures))
        object.__setattr__(self, "_lecture_ids", frozenset(lecture.id for lecture in self.lectures))
        object.__setattr__(self, "_subject_names", frozenset(lecture.subject.name for lecture in self.lectures))
        mask = 0
        for lecture in self.lectures:
            # 선택된 모든 강의의 시간 마스크를 합쳐 충돌 검사에 사용한다.
            mask |= lecture.time_mask
        object.__setattr__(self, "_time_mask", mask)

    @property
    def credits(self) -> float:
        return self._credits

    @property
    def lecture_ids(self) -> frozenset[str]:
        return self._lecture_ids

    @property
    def subject_names(self) -> frozenset[str]:
        return self._subject_names

    @property
    def time_mask(self) -> int:
        return self._time_mask

    def has_time_conflict(self, lecture: Lecture) -> bool:
        if self.time_mask and lecture.time_mask:
            # 마스크가 있으면 비트 연산만으로 겹치는 시간을 빠르게 확인한다.
            return bool(self.time_mask & lecture.time_mask)
        return any(slot.overlaps(other) for existing in self.lectures for slot in existing.time_slots for other in lecture.time_slots)

    def add(self, lecture: Lecture) -> "Schedule":
        # 기존 시간표를 바꾸지 않고 새 강의를 포함한 시간표 객체를 만든다.
        return Schedule(self.lectures + (lecture,))

    def raw_courses(self) -> list[dict]:
        return [dict(lecture.raw) for lecture in self.lectures]
