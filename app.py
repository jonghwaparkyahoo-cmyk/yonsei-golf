import streamlit as st
import pandas as pd

st.set_page_config(page_title="연세대 골프 대회 스코어보드", layout="centered", page_icon="⛳")

# --- 1. 코스 파(Par) 정보 (총 72 파) ---
PAR_LIST = [4, 4, 4, 3, 4, 5, 3, 5, 4, 4, 5, 3, 4, 4, 3, 5, 4, 4]

# --- 2. 데이터 세션 초기화 (조편성 및 핸디캡, 스코어) ---
if 'scores' not in st.session_state:
    st.session_state.scores = {}  # {선수명: {홀번호: 타수차}}

# 조편성 시트 및 핸디캡 구조를 반영한 실전 데이터 구조
# (실제 조편성 시트가 나오면 이 부분에 시트 연동 코드가 들어가게 됩니다)
if 'groups' not in st.session_state:
    st.session_state.groups = {
        "1A조": {
            "start_hole": 1,
            "players": {
                "김은혁": {"hcap": 23.0},
                "이은홍": {"hcap": 25.0},
                "박주원": {"hcap": "NA"}
            }
        },
        "5A조": {
            "start_hole": 5,
            "players": {
                "노재호": {"hcap": 21.0},
                "곽재영": {"hcap": 12.5},
                "최성식": {"hcap": "NA"}
            }
        }
    }

st.title("⛳ 연세대 골프 대회 모바일 스코어보드")
st.markdown("---")

menu = st.sidebar.radio("메뉴 선택", ["📝 스코어 입력", "🏆 실시간 리더보드", "⚙️ 운영진 관리"])

# ==========================================
# [메뉴 1] 스코어 입력 (통합 테이블 + 단일 홀 입력 및 앞뒤 홀 디스플레이)
# ==========================================
if menu == "📝 스코어 입력":
    st.header("📝 홀별 통합 스코어 입력")
    
    group_list = list(st.session_state.groups.keys())
    group_name = st.selectbox("조 선택", group_list)
    group_info = st.session_state.groups[group_name]
    start_hole = group_info["start_hole"]
    players_info = group_info["players"]
    
    st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식)")
    
    # 시작 홀부터 순서대로 18홀 순환 시퀀스 생성
    hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
    
    # 현재 집중해서 입력할 홀의 순번 관리 (0 ~ 17번째 홀)
    hole_idx_key = f"current_hole_idx_{group_name}"
    if hole_idx_key not in st.session_state:
        st.session_state[hole_idx_key] = 0
        
    current_idx = st.session_state[hole_idx_key]
    current_course_hole = hole_sequence[current_idx]
    current_par = PAR_LIST[current_course_hole - 1]
    
    # 상단 네비게이션: 앞뒤 홀로 이동하는 버튼과 현재 위치 표시
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 이전 홀") and current_idx > 0:
            st.session_state[hole_idx_key] -= 1
            st.rerun()
    with col_info:
        st.markdown(f"<div style='text-align: center;'><b>전체 {current_idx + 1}번째 홀</b><br>코스 {current_course_hole}번 (Par {current_par})</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("다음 홀 ▶") and current_idx < 17:
            st.session_state[hole_idx_key] += 1
            st.rerun()
            
    st.markdown("---")
    
    # 앞뒤 홀 참고 디스플레이 (이전 홀과 다음 홀 정보 간략 표시)
    prev_h = hole_sequence[current_idx - 1] if current_idx > 0 else "-"
    next_h = hole_sequence[current_idx + 1] if current_idx < 17 else "-"
    st.caption(f"👀 [참고] 이전 홀(코스 {prev_h}번) ➔ **현재 입력 홀(코스 {current_course_hole}번, Par {current_par})** ➔ 다음 홀(코스 {next_h}번)")

    # 모든 선수들이 한눈에 들어오는 통합 테이블 형태로 점수 입력
    with st.form(key=f"unified_score_form_{group_name}_{current_idx}"):
        st.markdown(f"#### 🏌️‍♂️ {current_idx + 1}번째 홀 (코스 {current_course_hole}번홀, Par {current_par}) 스코어 입력")
        
        form_inputs = {}
        
        # 테이블 헤더 느낌의 컬럼 구성
        for player, p_data in players_info.items():
            if player not in st.session_state.scores:
                st.session_state.scores[player] = {}
                
            current_val = st.session_state.scores[player].get(current_course_hole, 0)
            
            # 더블파 맥스 제한 (파3: +3, 파4: +4, 파5: +5)
            max_over = current_par
            options = list(range(-2, max_over + 1))  # -2(이글) ~ 더블파(+Par)
            if current_val not in options:
                current_val = 0
                
            col_p1, col_p2 = st.columns([1, 2])
            with col_p1:
                st.markdown(f"**{player}** (Hcap: {p_data['hcap']})")
            with col_p2:
                score_diff = st.selectbox(
                    f"{player} 성적 선택",
                    options=options,
                    index=options.index(current_val) if current_val in options else 2,
                    format_func=lambda x: "이글(-2)" if x==-2 else ("버디(-1)" if x==-1 else ("파(0)" if x==0 else f"+{x}")),
                    key=f"input_{player}_{current_course_hole}",
                    label_visibility="collapsed"
                )
                form_inputs[player] = score_diff
            st.write("") # 간격 조정
            
        submitted = st.form_submit_button("💾 이 홀의 스코어 일괄 저장")
        if submitted:
            for player, diff in form_inputs.items():
                st.session_state.scores[player][current_course_hole] = diff
            st.success(f"{current_idx + 1}번째 홀 스코어가 저장되었습니다!")

# ==========================================
# [메뉴 2] 실시간 리더보드 (이름, Gross, 핸디캡, Net, 소화홀/현재위치, NA 하단정렬)
# ==========================================
elif menu == "🏆 실시간 리더보드":
    st.header("🏆 실시간 리더보드 (Net 순위)")
    
    leaderboard_data = []
    
    for group_name, info in st.session_state.groups.items():
        start_hole = info["start_hole"]
        hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
        
        for player, p_data in info["players"].items():
            hcap = p_data["hcap"]
            p_scores = st.session_state.scores.get(player, {})
            played_count = len(p_scores)
            
            gross_total = 0
            for h, diff in p_scores.items():
                gross_total += (PAR_LIST[h-1] + diff)
                
            has_hcap = (hcap != "NA")
            net_score = (gross_total - float(hcap)) if (played_count > 0 and has_hcap) else "-"
            
            if played_count > 0:
                current_nth_hole = played_count if played_count <= 18 else 18
                current_course_hole = hole_sequence[current_nth_hole - 1]
                status = f"{played_count}/18홀 (코스 {current_course_hole}번홀 진행중)"
            else:
                status = "0/18홀 (출발 대기)"
                
            leaderboard_data.append({
                "선수명": player,
                "Gross": gross_total if played_count > 0 else "-",
                "핸디캡": hcap,
                "Net": net_score,
                "소화홀/현재위치": status,
                "Sort_HasHcap": 0 if has_hcap else 1,
                "Sort_Net": net_score if (played_count > 0 and has_hcap) else 999
            })
            
    df_lb = pd.DataFrame(leaderboard_data)
    if not df_lb.empty:
        # 핸디캡 있는 선수 우선 정렬 후 Net 점수 낮은 순, NA 선수는 하단 배치
        df_lb = df_lb.sort_values(by=["Sort_HasHcap", "Sort_Net"], ascending=[True, True])
        df_display = df_lb[["선수명", "Gross", "핸디캡", "Net", "소화홀/현재위치"]].reset_index(drop=True)
        df_display.index += 1  # 1위부터 순위 표시
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없습니다.")

# ==========================================
# [메뉴 3] 운영진 관리 (조편성 및 핸디캡 연동 관리)
# ==========================================
elif menu == "⚙️ 운영진 관리":
    st.header("⚙️ 운영진 관리 패널")
    st.markdown("조편성 시트와 핸디캡 데이터베이스를 기반으로 한 조 및 선수 관리 화면입니다.")
    
    for group_name, info in st.session_state.groups.items():
        with st.expander(f"조: {group_name} (시작홀: {info['start_hole']}번)"):
            st.write(f"**편성된 선수 및 핸디캡:**")
            for p, d in info["players"].items():
                st.text(f"- {p} (핸디캡: {d['hcap']})")