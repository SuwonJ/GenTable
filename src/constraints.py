from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.models import Lecture, Schedule, StudentProfile


class HardConstraint(Protocol):
    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        ...

    def is_satisfied(self, schedule: Schedule) -> bool:
        ...


@dataclass(frozen=True)
class NoTimeConflictConstraint:
    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        # 이미 선택된 강의와 시간이 겹치면 후보 조합에 추가하지 않는다.
        return not schedule.has_time_conflict(lecture)

    def is_satisfied(self, schedule: Schedule) -> bool:
        return True


@dataclass(frozen=True)
class NoDuplicateSubjectConstraint:
    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        # 같은 과목의 다른 분반이 동시에 들어가는 것을 막는다.
        return lecture.subject.name not in schedule.subject_names

    def is_satisfied(self, schedule: Schedule) -> bool:
        return len(schedule.subject_names) == len(schedule.lectures)


@dataclass(frozen=True)
class CreditRangeConstraint:
    min_credits: float
    max_credits: float

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        # 최대 학점은 탐색 중 바로 가지치기할 수 있는 조건이다.
        return schedule.credits + lecture.subject.credits <= self.max_credits

    def is_satisfied(self, schedule: Schedule) -> bool:
        return self.min_credits <= schedule.credits <= self.max_credits


@dataclass(frozen=True)
class RequiredLectureConstraint:
    lecture_ids: frozenset[str]

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        return True

    def is_satisfied(self, schedule: Schedule) -> bool:
        return self.lecture_ids.issubset(schedule.lecture_ids)


@dataclass(frozen=True)
class RequiredSubjectConstraint:
    subject_names: frozenset[str]

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        return True

    def is_satisfied(self, schedule: Schedule) -> bool:
        return self.subject_names.issubset(schedule.subject_names)


@dataclass(frozen=True)
class ExcludedLectureConstraint:
    lecture_ids: frozenset[str]
    required_lecture_ids: frozenset[str] = frozenset()

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        # 장바구니 필수 과목은 제외 목록에 있어도 사용자가 고정한 선택을 우선한다.
        return lecture.id not in self.lecture_ids or lecture.id in self.required_lecture_ids

    def is_satisfied(self, schedule: Schedule) -> bool:
        return not (schedule.lecture_ids - self.required_lecture_ids).intersection(self.lecture_ids)


@dataclass(frozen=True)
class AlternativeGroupConstraint:
    groups: tuple[frozenset[str], ...]

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        selected_ids = schedule.lecture_ids
        for group in self.groups:
            if lecture.id not in group:
                continue
            if group.intersection(selected_ids):
                # 대체 그룹 안에서는 이미 하나를 골랐다면 추가 선택하지 않는다.
                return False
        return True

    def is_satisfied(self, schedule: Schedule) -> bool:
        ids = schedule.lecture_ids
        return all(group.intersection(ids) for group in self.groups)


@dataclass(frozen=True)
class StudentEligibilityConstraint:
    profile: StudentProfile
    override_lecture_ids: frozenset[str] = frozenset()

    def can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        if lecture.id in self.override_lecture_ids:
            # 사용자가 직접 고정한 강의는 프로필 제한보다 우선한다.
            return True
        return lecture.target.is_eligible(self.profile.grade, self.profile.department)

    def is_satisfied(self, schedule: Schedule) -> bool:
        return all(
            lecture.id in self.override_lecture_ids
            or lecture.target.is_eligible(self.profile.grade, self.profile.department)
            for lecture in schedule.lectures
        )


@dataclass(frozen=True)
class ConstraintSet:
    hard_constraints: tuple[HardConstraint, ...]


class ConstraintRegistry:
    @staticmethod
    def from_request(
        *,
        profile: StudentProfile,
        min_credits: float,
        max_credits: float,
        required_lecture_ids: frozenset[str],
        required_subject_names: frozenset[str],
        excluded_lecture_ids: frozenset[str],
        alternative_groups: tuple[frozenset[str], ...] = (),
        enforce_profile_eligibility: bool = True,
    ) -> ConstraintSet:
        # 모든 요청에 공통으로 필요한 강제 제약을 먼저 구성한다.
        hard: list[HardConstraint] = [
            NoTimeConflictConstraint(),
            NoDuplicateSubjectConstraint(),
            CreditRangeConstraint(min_credits=min_credits, max_credits=max_credits),
            RequiredLectureConstraint(required_lecture_ids),
            RequiredSubjectConstraint(required_subject_names),
            ExcludedLectureConstraint(excluded_lecture_ids, required_lecture_ids),
            AlternativeGroupConstraint(alternative_groups),
        ]
        if enforce_profile_eligibility:
            # 생성 탭에서는 학년/학과 조건을 수강 가능 여부 제약으로 적용한다.
            hard.append(StudentEligibilityConstraint(profile, override_lecture_ids=required_lecture_ids))

        return ConstraintSet(hard_constraints=tuple(hard))
