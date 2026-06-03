from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from src.domain.models import Lecture


class LectureCatalog:
    def __init__(self, lectures: Iterable[Lecture]):
        # 입력 순서를 튜플로 고정해 탐색 중 강의 목록이 바뀌지 않게 한다.
        self._lectures = tuple(lectures)
        # 과목번호는 분반을 직접 지정할 때 사용하므로 단일 조회용 딕셔너리로 만든다.
        self._by_id = {lecture.id: lecture for lecture in self._lectures}
        by_subject: dict[str, list[Lecture]] = defaultdict(list)
        for lecture in self._lectures:
            # 같은 과목명에 여러 분반이 있을 수 있어 목록으로 모은다.
            by_subject[lecture.subject.name].append(lecture)
        # 외부에서 인덱스 목록을 수정하지 못하도록 튜플로 마감한다.
        self._by_subject = {name: tuple(items) for name, items in by_subject.items()}

    def by_id(self, lecture_id: str) -> Lecture | None:
        # 존재하지 않는 과목번호는 빈값으로 돌려 호출부가 경고를 만들게 한다.
        return self._by_id.get(lecture_id)

    def by_subject_name(self, name: str) -> tuple[Lecture, ...]:
        return self._by_subject.get(name, ())

    def all(self) -> tuple[Lecture, ...]:
        return self._lectures
