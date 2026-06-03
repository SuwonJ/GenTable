# 조회 패키지는 강의 조회 인덱스를 제공한다.
# 엔진은 과목번호와 과목명으로 강의를 찾을 때 강의 조회 객체를 사용한다.
# 외부 모듈은 하위 파일 경로 대신 이 패키지에서 공개 클래스를 가져올 수 있다.
# 공개 목록은 불필요한 객체 노출을 막는다.
# 실제 인덱스 구성 로직은 조회 파일에 둔다.
from src.catalog.catalog import LectureCatalog

__all__ = ["LectureCatalog"]
