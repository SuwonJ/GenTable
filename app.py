from pathlib import Path

import os
import re
import urllib.parse
import streamlit as st

from src.data_loader import load_catalog, process_files
from src.services.scheduler_service import generate_timetables
from src.services.tagging_service import ensure_tags, get_all_unique_tags
from src.services.criteria_service import parse_criterion
from src.services.clustering_service import find_similar_courses
from src.presentation.dataframe_exporter import timetable_to_frame
from src.presentation.ui_state import (
    DAY_ORDER,
    TOP_N_MAX,
    TOP_N_MIN,
    add_all_to_group_batch,
    add_to_group,
    add_group,
    alternative_group_sets,
    clear_group,
    delete_group,
    ensure_state,
    export_config,
    format_course_line,
    generation_filter_state,
    group_keys,
    group_name_map,
    has_internal_conflict,
    highlight_target_text,
    import_config,
    matched_rule_text,
    matched_target_pills,
    remove_from_bucket,
    remove_from_group,
    render_course_meta,
    render_pills,
    render_timetable,
    result_frame,
    search_courses,
    selection_status_meta,
    sync_group_name,
    target_badges,
    target_departments,
    update_bucket,
)


def get_svg_as_data_uri(file_path: str, fill_color: str = None) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    if not path.exists():
        return ""
    svg_content = path.read_text(encoding="utf-8")
    if fill_color:
        if 'fill="' in svg_content:
            svg_content = re.sub(r'fill="[^"]+"', f'fill="{fill_color}"', svg_content)
        else:
            svg_content = svg_content.replace("<svg ", f'<svg fill="{fill_color}" ')

    encoded_svg = urllib.parse.quote(svg_content)
    return f"data:image/svg+xml,{encoded_svg}"


TABLE_DIR = Path(__file__).parent / "tables"


def load_catalog_from_uploads(uploaded_files: list) -> dict:
    files = []
    filenames = []
    for f in uploaded_files:
        files.append(f)
        filenames.append(f.name)
    return process_files(files, filenames=filenames)


def render_search_tab(results: list[dict], active_group: str, filter_state: dict) -> str:
    course_tags = st.session_state.get("course_tags", {})
    catalog_by_id = {c["course_id"]: c for c in st.session_state.get("catalog", {}).get("courses", [])}
    for course in results[:24]:
        with st.container(border=True):
            info_col, action_col = st.columns([3.2, 1])
            with info_col:
                target_pills = target_badges(course)
                matched_pills = matched_target_pills(course, filter_state)
                status_text, status_class = selection_status_meta(course["course_id"])
                st.markdown(
                    f'<div class="status-chip {status_class}">{status_text}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**{course['name']}** `{course['course_id']}`  \n"
                    f"{course['category_label']}"
                )
                # 과목 태그 pill 표시
                tags = course_tags.get(str(course["course_id"]), [])
                if tags:
                    tag_html = " ".join(
                        f'<span style="display:inline-block;margin:0.08rem 0.15rem;padding:0.12rem 0.4rem;'
                        f'border-radius:999px;background:#eef0fb;color:#3046a1;border:1px solid #bcc5ee;'
                        f'font-size:0.7rem;font-weight:600;">{t}</span>'
                        for t in tags
                    )
                    st.markdown(tag_html, unsafe_allow_html=True)
                st.markdown(render_course_meta(course), unsafe_allow_html=True)
                if target_pills:
                    st.markdown(render_pills(target_pills, matched_pills), unsafe_allow_html=True)
                matched_text = matched_rule_text(course, filter_state)
                if matched_text:
                    st.caption(f"조건 일치: {matched_text}")
                # 유사 과목 추천
                if course_tags:
                    with st.expander("💡 유사한 과목", expanded=False):
                        similar = find_similar_courses(
                            str(course["course_id"]), course_tags, catalog_by_id, top_n=3,
                        )
                        if similar:
                            for s in similar:
                                shared = ", ".join(s["shared_tags"])
                                st.caption(
                                    f"{s['name']} (유사도: {s['similarity']:.0%}) "
                                    f"[공통: {shared}]"
                                )
                        else:
                            st.caption("유사한 과목이 없습니다.")
                with st.expander("수강대상 원문", expanded=False):
                    st.markdown(
                        f"수강대상: {highlight_target_text(course, filter_state)}",
                        unsafe_allow_html=True,
                    )
            with action_col:
                # 아이콘 버튼: SVG 배경으로 렌더링하고 라벨 텍스트는 숨깁니다.
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown('<span class="icon-marker basket-marker"></span>', unsafe_allow_html=True)
                    if st.button("장바구니", key=f"basket_{course['course_id']}", help="장바구니 (필수)",
                                 use_container_width=True, type="primary"):
                        update_bucket(course["course_id"], "basket")
                        st.rerun()
                with c2:
                    st.markdown('<span class="icon-marker wish-marker"></span>', unsafe_allow_html=True)
                    if st.button("위시", key=f"wish_{course['course_id']}", help="위시 (후보)", use_container_width=True):
                        update_bucket(course["course_id"], "wish")
                        st.rerun()
                with c3:
                    st.markdown('<span class="icon-marker exclude-marker"></span>', unsafe_allow_html=True)
                    if st.button("제외", key=f"exclude_{course['course_id']}", help="제외", use_container_width=True):
                        update_bucket(course["course_id"], "excluded")
                        st.rerun()

                group_list = group_keys()
                if group_list:
                    st.selectbox(
                        "그룹 선택",
                        options=["그룹 담기..."] + group_list,
                        format_func=lambda key: group_name_map().get(key, key) if key != "그룹 담기..." else key,
                        key=f"group_pick_{course['course_id']}",
                        label_visibility="collapsed",
                        on_change=lambda cid=course['course_id']: (
                            add_to_group(cid, st.session_state[f"group_pick_{cid}"])
                            if st.session_state[f"group_pick_{cid}"] != "그룹 담기..."
                            else None
                        )
                    )

    with st.expander("검색 결과 표 보기", expanded=False):
        st.dataframe(result_frame(results), use_container_width=True, hide_index=True)
    return active_group


def render_group_panel(catalog_by_id: dict[str, dict], group_key: str) -> None:
    group = st.session_state.alternative_groups[group_key]
    courses = [catalog_by_id[course_id] for course_id in group["ids"] if course_id in catalog_by_id]
    with st.container(border=True):
        header1, header2 = st.columns([3, 1])
        header1.text_input(
            "그룹 이름",
            value=group["name"],
            key=f"name_{group_key}",
            on_change=sync_group_name,
            args=(group_key,),
        )
        if header2.button("그룹 비우기", key=f"clear_{group_key}", use_container_width=True):
            clear_group(group_key)
        if header2.button("그룹 삭제", key=f"delete_{group_key}", use_container_width=True):
            delete_group(group_key)
            st.rerun()
        st.caption("이 그룹의 과목들 중 하나 이상이 시간표에 포함되면 됩니다.")
        if not courses:
            st.caption("아직 담긴 과목이 없습니다.")
            return
        if has_internal_conflict(courses):
            st.warning("그룹 내 과목끼리는 서로 충돌해도 괜찮습니다. 이 중 하나만 시간표에 포함됩니다.")
        for course in courses:
            row1, row2 = st.columns([6, 1])
            row1.caption(format_course_line(course))
            if row2.button("제거", key=f"remove_{group_key}_{course['course_id']}", use_container_width=True):
                remove_from_group(course["course_id"], group_key)
        st.dataframe(timetable_to_frame(courses), use_container_width=True, hide_index=True)


def render_basket_tab(catalog_by_id: dict[str, dict]) -> None:
    st.subheader("그룹바구니")
    left, right = st.columns([1, 2])

    with left:
        with st.container(border=True):
            st.markdown("#### 고정/우선 선택")
            basket_courses = [catalog_by_id[course_id] for course_id in st.session_state.preferred_ids if
                              course_id in catalog_by_id]
            wish_courses = [catalog_by_id[course_id] for course_id in st.session_state.candidate_ids if
                            course_id in catalog_by_id]
            excluded_courses = [catalog_by_id[course_id] for course_id in st.session_state.excluded_ids if
                                course_id in catalog_by_id]

            st.write(f"장바구니(필수): {len(basket_courses)}개")
            for course in basket_courses:
                st.caption(format_course_line(course))
            st.write(f"위시(후보): {len(wish_courses)}개")
            for course in wish_courses:
                st.caption(format_course_line(course))
            st.write(f"제외: {len(excluded_courses)}개")
            for course in excluded_courses:
                st.caption(format_course_line(course))

        preview_courses = basket_courses + [
            course
            for course in wish_courses
            if course["course_id"] not in st.session_state.preferred_ids
        ]
        with st.container(border=True):
            st.markdown("#### 고정 선택 미리보기")
            if preview_courses:
                if has_internal_conflict(preview_courses):
                    st.warning("선택한 과목끼리 시간 충돌이 있습니다.")
                st.dataframe(timetable_to_frame(preview_courses), use_container_width=True, hide_index=True)
            else:
                st.caption("아직 선택한 과목이 없습니다.")

    with right:
        st.markdown("#### 그룹바구니")
        if st.button("새 그룹 추가", key="add_group_in_tab", use_container_width=True):
            add_group()
            st.rerun()

        keys = group_keys()
        tabs = st.tabs([st.session_state.alternative_groups[key]["name"] for key in keys]) if keys else []
        for tab, group_key in zip(tabs, keys):
            with tab:
                render_group_panel(catalog_by_id, group_key)


def render_summary_panel(catalog_by_id: dict[str, dict], search_results: list[dict] = None) -> None:
    if not catalog_by_id and (st.session_state.preferred_ids or st.session_state.alternative_groups):
        st.warning("강의 데이터를 먼저 불러와야 합니다.")

    basket_courses = [catalog_by_id[course_id] for course_id in st.session_state.preferred_ids if
                      course_id in catalog_by_id]
    wish_courses = [catalog_by_id[course_id] for course_id in st.session_state.candidate_ids if
                    course_id in catalog_by_id]
    excluded_courses = [catalog_by_id[course_id] for course_id in st.session_state.excluded_ids if
                        course_id in catalog_by_id]

    with st.expander(f"장바구니 ({len(basket_courses)})", expanded=True):
        if not basket_courses:
            st.caption("비어 있음")
        for course in basket_courses:
            row1, row2 = st.columns([4, 1])
            row1.caption(f"{course['name']}")
            if row2.button("X", key=f"sum_basket_{course['course_id']}", help="제거"):
                remove_from_bucket(course["course_id"])
                st.rerun()

    with st.expander(f"위시 ({len(wish_courses)})", expanded=False):
        if not wish_courses:
            st.caption("비어 있음")
        for course in wish_courses:
            row1, row2 = st.columns([4, 1])
            row1.caption(f"{course['name']}")
            if row2.button("X", key=f"sum_wish_{course['course_id']}", help="제거"):
                remove_from_bucket(course["course_id"])
                st.rerun()

    with st.expander(f"그룹바구니 ({len(alternative_group_sets())})", expanded=False):
        if search_results:
            g_keys = group_keys()
            g_names = group_name_map()
            if g_keys:
                target_group = st.selectbox(
                    "일괄 담기 대상",
                    options=g_keys,
                    format_func=lambda k: g_names.get(k, k),
                    key="batch_group_target_merged",
                )
                if st.button("검색 결과 전체 담기", use_container_width=True, key="batch_group_add_merged"):
                    add_all_to_group_batch(search_results, target_group)
                    st.rerun()
            st.divider()

        keys = group_keys()
        if not keys:
            st.caption("그룹 없음")
        for group_key in keys:
            group = st.session_state.alternative_groups[group_key]
            ids = group["ids"]
            with st.expander(f"{group['name']} ({len(ids)})", expanded=False):
                for course_id in ids:
                    if course_id in catalog_by_id:
                        c = catalog_by_id[course_id]
                        row1, row2 = st.columns([4, 1])
                        row1.caption(f"{c['name']}")
                        if row2.button("X", key=f"sum_grp_{group_key}_{course_id}", help="제거"):
                            remove_from_group(course_id, group_key)
                            st.rerun()

    with st.expander(f"제외 ({len(excluded_courses)})", expanded=False):
        if not excluded_courses:
            st.caption("비어 있음")
        for course in excluded_courses:
            row1, row2 = st.columns([4, 1])
            row1.caption(f"{course['name']}")
            if row2.button("X", key=f"sum_excl_{course['course_id']}", help="해제"):
                remove_from_bucket(course["course_id"])
                st.rerun()


def generate_and_store_timetables(
        catalog: dict,
        controls: dict,
        locked_ids: set[str] | None = None,
        extra_excluded_ids: set[str] | None = None,
) -> None:
    preferred_ids = set(st.session_state.preferred_ids)
    candidate_ids = set(st.session_state.candidate_ids)
    excluded_ids = set(st.session_state.excluded_ids)

    if locked_ids:
        preferred_ids |= set(locked_ids)
        candidate_ids -= set(locked_ids)
        excluded_ids -= set(locked_ids)

    if extra_excluded_ids:
        excluded_ids |= set(extra_excluded_ids)
        preferred_ids -= set(extra_excluded_ids)
        candidate_ids -= set(extra_excluded_ids)

    # LLM 커스텀 기준 전달
    custom_criteria = st.session_state.get("custom_criteria", []) or None
    course_tags = st.session_state.get("course_tags", {}) or None

    candidates, info = generate_timetables(
        catalog=catalog,
        grade=controls["grade"],
        semester=controls["semester"],
        include_regex=controls["include_regex"],
        exclude_regex=controls["exclude_regex"],
        preferred_ids=preferred_ids,
        candidate_ids=candidate_ids,
        excluded_ids=excluded_ids,
        alternative_groups=alternative_group_sets(),
        min_credits=controls["min_credits"],
        max_credits=controls["max_credits"],
        top_n=controls["top_n"],
        weights=controls["weights"],
        filter_state=generation_filter_state(controls),
        custom_criteria=custom_criteria,
        course_tags=course_tags,
    )
    st.session_state.candidates = candidates
    st.session_state.last_info = info
    for key in list(st.session_state.keys()):
        if key.startswith("removed_candidate_"):
            del st.session_state[key]


def render_results_tab(catalog: dict, controls: dict) -> None:
    st.subheader("시간표 생성")
    st.caption("장바구니(필수), 위시(후보), 그룹바구니를 모두 반영해 후보 시간표를 생성합니다.")
    with st.container(border=True):
        department_options = ["전체"] + target_departments(catalog["courses"])
        if controls.get("department", "전체") not in department_options:
            controls["department"] = "전체"
        c1, c2, c3 = st.columns(3)
        controls["grade"] = c1.selectbox("학년", ["전체", "1", "2", "3", "4"],
                                         index=["전체", "1", "2", "3", "4"].index(controls["grade"]))
        controls["semester"] = c2.selectbox("학기", ["전체", "1", "2"], index=["전체", "1", "2"].index(controls["semester"]))
        controls["department"] = c3.selectbox("학과/학부", department_options,
                                              index=department_options.index(controls.get("department", "전체")))
        c4, c5 = st.columns(2)
        controls["min_credits"] = c4.slider("최소 학점", 0, 21, controls["min_credits"])
        controls["max_credits"] = c5.slider("최대 학점", 6, 24, controls["max_credits"])
        controls["top_n"] = st.slider("보여줄 후보 개수", TOP_N_MIN, TOP_N_MAX, controls["top_n"])
        c8, c9 = st.columns(2)
        controls["include_regex"] = c8.text_input("추가 포함 정규식", controls["include_regex"])
        controls["exclude_regex"] = c9.text_input("추가 제외 정규식", controls["exclude_regex"])
        st.markdown("#### 가중치")
        w1, w2, w3 = st.columns(3)
        controls["weights"]["prefer_free_day"] = w1.slider("공강일 선호", 0, 5, controls["weights"]["prefer_free_day"])
        controls["weights"]["avoid_morning"] = w2.slider("오전 수업 회피", 0, 5, controls["weights"]["avoid_morning"])
        controls["weights"]["avoid_gap"] = w3.slider("애매한 공강 회피", 0, 5, controls["weights"]["avoid_gap"])
        st.caption("생성 탭은 검색 탭의 카테고리/요일/시간 필터를 직접 반영하지 않습니다.")
        p1, p2, p3 = st.columns(3)
        if p1.button("아침회피 프리셋", use_container_width=True):
            controls["weights"]["prefer_free_day"] = 1
            controls["weights"]["avoid_morning"] = 5
            controls["weights"]["avoid_gap"] = 1
            st.rerun()
        if p2.button("공강선호 프리셋", use_container_width=True):
            controls["weights"]["prefer_free_day"] = 5
            controls["weights"]["avoid_morning"] = 2
            controls["weights"]["avoid_gap"] = 1
            st.rerun()
        if p3.button("균형 프리셋", use_container_width=True):
            controls["weights"]["prefer_free_day"] = 3
            controls["weights"]["avoid_morning"] = 2
            controls["weights"]["avoid_gap"] = 3
            st.rerun()

    # ─── AI 커스텀 기준 섹션 ───
    api_key = st.session_state.get("gemini_api_key", "")
    if api_key:
        with st.container(border=True):
            st.markdown("#### AI 가중치 세터")
            st.caption('"점심시간 비워줘", "수학 싫어", "화목 오후에만" 같은 자연어로 기준을 입력하세요.')
            cr_col1, cr_col2 = st.columns([4, 1])
            with cr_col1:
                criterion_input = st.text_input(
                    "커스텀 기준 입력",
                    placeholder="예: 점심시간 비워줘, 수학 싫어, 연강 2시간 제한...",
                    label_visibility="collapsed",
                    key="criterion_input",
                )
            with cr_col2:
                add_clicked = st.button("추가", key="add_criterion", use_container_width=True, type="primary")

            if add_clicked and criterion_input:
                try:
                    tags = get_all_unique_tags(st.session_state.get("course_tags", {}))
                    new_criterion = parse_criterion(criterion_input, api_key, tags)
                    st.session_state.custom_criteria.append(new_criterion)
                    st.toast(f"기준 추가: {new_criterion.label}")
                    st.rerun()
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        st.error(
                            "⚠️ **Gemini API 호출 한도가 초과되었습니다 (일일 한도: 20회).**\n\n"
                            "현재 계정의 일일 무료 할당량이 소진되었습니다. 잠시 대기 후 시도하시거나 다른 API 키를 등록해 주세요."
                        )
                    else:
                        st.error(f"기준 파싱 실패: {e}")

            # 적용 중인 기준 표시
            criteria = st.session_state.get("custom_criteria", [])
            if criteria:
                st.markdown("**적용 중인 기준:**")
                for idx, c in enumerate(criteria):
                    cr_display, cr_del = st.columns([5, 1])
                    cr_display.markdown(
                        f'<span style="display:inline-block;padding:0.2rem 0.6rem;'
                        f'border-radius:999px;background:#eef0fb;color:#3046a1;'
                        f'border:1px solid #bcc5ee;font-size:0.82rem;font-weight:600;">'
                        f'{c.label}</span>',
                        unsafe_allow_html=True,
                    )
                    if cr_del.button("×", key=f"del_criterion_{idx}", help="기준 삭제"):
                        st.session_state.custom_criteria.pop(idx)
                        st.rerun()
            else:
                st.caption("아직 커스텀 기준이 없습니다. 위에서 자연어로 추가해보세요.")
        if st.button("시간표 생성", type="primary", use_container_width=True):
            with st.spinner("시간표 후보를 계산하고 있습니다..."):
                generate_and_store_timetables(catalog, controls)

    info = st.session_state.get("last_info")
    if info:
        st.info(
            f"필수 반영 {info['required_selected']}개, 필터 후 후보 {info['filtered_count']}개, "
            f"시간표 {info['candidate_count']}개 생성됨."
        )

    candidates = st.session_state.get("candidates", [])
    if not candidates:
        st.caption("아직 생성된 시간표가 없습니다.")
        return

    rank_options = [candidate["rank"] for candidate in candidates]
    selected_rank = st.segmented_control(
        "후보 선택",
        options=rank_options,
        default=rank_options[0],
        format_func=lambda value: f"후보 {value}",
        key="candidate_picker",
        label_visibility="collapsed",
    )
    if selected_rank is None:
        selected_rank = rank_options[0]
    selected_candidate = next(candidate for candidate in candidates if candidate["rank"] == selected_rank)
    groups = alternative_group_sets()
    action = render_timetable(selected_candidate, groups)
    if action:
        generate_and_store_timetables(
            catalog,
            controls,
            locked_ids=action["locked_ids"],
            extra_excluded_ids=action["excluded_ids"],
        )
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="GenTable", page_icon="assets/gtlogo.svg", layout="wide")

    basket_icon = get_svg_as_data_uri("assets/basket.svg", "white")
    wish_icon = get_svg_as_data_uri("assets/wish.svg", "#a75434")
    exclude_icon = get_svg_as_data_uri("assets/exclude.svg", "#a75434")
    search_icon = get_svg_as_data_uri("assets/search.svg")

    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        css_content = css_content.replace("{search_icon}", search_icon)
        css_content = css_content.replace("{basket_icon}", basket_icon)
        css_content = css_content.replace("{wish_icon}", wish_icon)
        css_content = css_content.replace("{exclude_icon}", exclude_icon)
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
    ensure_state()

    # ─── API 키 (우선순위: st.secrets -> os.environ) ───
    GEMINI_API_KEY = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    if not GEMINI_API_KEY:
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    st.session_state["gemini_api_key"] = GEMINI_API_KEY

    # 사이드바 레이아웃
    with st.sidebar:
        with st.container():
            r1, r2 = st.columns(2)
            r1.metric("개설 강의", len(st.session_state.catalog["courses"]) if "catalog" in st.session_state else 0)
            r2.metric("장바구니", len(st.session_state.preferred_ids))
            r3, r4 = st.columns(2)
            r3.metric("그룹 수", len(alternative_group_sets()))
            r4.metric("제외 과목", len(st.session_state.excluded_ids))

    if "catalog" not in st.session_state:
        if TABLE_DIR.exists():
            st.session_state.catalog = load_catalog(TABLE_DIR)
        else:
            st.session_state.catalog = {"courses": [], "curriculum_required": {}, "warnings": []}

    catalog = st.session_state.catalog
    catalog_by_id = {course["course_id"]: course for course in catalog["courses"]}

    # ─── 카탈로그 로드 후 자동 태깅 ───
    if catalog["courses"] and not st.session_state.get("course_tags"):
        catalog_by_id_for_tag = {
            str(c["course_id"]): c for c in catalog["courses"]
        }
        with st.spinner("🏷️ 과목 AI 태깅 중... (최초 1회만 실행됩니다)"):
            try:
                tags = ensure_tags(catalog_by_id_for_tag, GEMINI_API_KEY)
                st.session_state.course_tags = tags
                tagged_count = sum(1 for v in tags.values() if v)
                st.toast(f"태깅 완료: {tagged_count}/{len(tags)}개 과목")
            except Exception as e:
                st.warning(f"자동 태깅 실패 (앱은 정상 작동합니다): {e}")
                st.session_state.course_tags = {}

    # 메인 영역
    header_logo, header_search = st.columns([1, 6])
    with header_logo:
        st.image("assets/gtlogo.svg")
    with header_search:
        query = st.text_input(
            "통합 검색",
            placeholder="과목명, 교수명, 과목번호, 교과영역, 시간, 수강대상 등을 공백으로 검색",
            label_visibility="collapsed",
            key="search_query",
        )

    results = []
    if catalog["courses"]:
        # 결과 필터링
        target_options = target_departments(catalog["courses"])
        quick1, quick2, quick3 = st.columns([1.1, 1.7, 1.1])

        with quick1:
            # label_visibility="collapsed"를 지우거나 "visible"로 변경
            selected_grade = st.selectbox("학년", ["전체", "1학년", "2학년", "3학년", "4학년"], index=0)
        with quick2:
            selected_department = st.selectbox("학부/학과", ["전체"] + target_options, index=0)
        with quick3:
            selected_day = st.selectbox("요일", ["전체"] + DAY_ORDER, index=0)

        target_grades = [] if selected_grade == "전체" else [selected_grade]
        target_department_filters = [] if selected_department == "전체" else [selected_department]
        day_filters = [] if selected_day == "전체" else [selected_day]

        results = search_courses(
            catalog["courses"],
            query=query,
            category_filters=[],  # Simplified for this pass
            day_filters=day_filters,
            time_filter="전체",
            target_grades=target_grades,
            target_departments=target_department_filters,
            hide_foreign_only=True,
            target_include_regex="",
            target_exclude_regex="",
        )

    # 사이드바 요약 패널
    with st.sidebar:
        render_summary_panel(catalog_by_id, results if query else [])

        st.divider()
        st.subheader("데이터 관리")
        uploaded_files = st.file_uploader(
            "강의 목록(CSV/Excel) 업로드",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            help="시간표 엑셀 파일들을 업로드하세요.",
            key="data_uploader"
        )
        if st.button("강의 데이터 로드", use_container_width=True, key="load_data_btn"):
            if uploaded_files:
                st.session_state.catalog = load_catalog_from_uploads(uploaded_files)
                st.success(f"{len(uploaded_files)}개 파일 로드 완료")
                st.rerun()
            else:
                st.warning("업로드된 파일이 없습니다.")
        with st.container(border=True):
            st.markdown("### 설정")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "저장",
                    export_config(),
                    file_name="aitimetable_config.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with c2:
                uploaded_file = st.file_uploader("불러오기", type="json", label_visibility="collapsed",
                                                 key="config_uploader")
                if uploaded_file is not None:
                    if st.button("적용", use_container_width=True, type="primary", key="apply_config_btn"):
                        try:
                            raw = uploaded_file.getvalue()
                            import_config(raw.decode("utf-8-sig"))
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")

    if not catalog["courses"]:
        st.info("사이드바 하단에서 강의 데이터를 먼저 업로드해주세요.")
        st.stop()

    tabs = st.tabs(["강의 탐색", "그룹바구니", "시간표 생성"])
    with tabs[0]:
        render_search_tab(results, "", {})
    with tabs[1]:
        render_basket_tab(catalog_by_id)
    with tabs[2]:
        render_results_tab(catalog, st.session_state.controls)


if __name__ == "__main__":
    main()
