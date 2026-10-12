import streamlit as st
import pandas as pd

st.set_page_config(page_title="연세대 골프 대회 리더보드", layout="centered")

# --- [1. 기본 설정 및 코스 파(Par) 정보] ---
# 18홀 기본 파 정보 (예시)
PAR_LIST = [4, 4, 3, 5, 4, 4, 3, 4, 5, 4, 3, 4, 5, 4, 4, 3, 5, 4] 

# --- [2. 조편성 및 데이터 (예시 데이터)] ---
# 실제 운영 시에는 'YS_handicap_2026' 또는 조편성 스프레드시트와 연동됩니다.
if 'scores' not in st.session_state:
    st.session_state.scores = {}  # {선수이름: {홀번호(1~18): 타수차(-2~+2)}}

# 조편성 정보 (조 이름, 시작홀, 조원 명단)
GROUPS = {
    "1조 (일반)": {"start_hole": 1, "players": ["김은혁", "이은홍", "박주원"]},
    "5A조 (샷건)": {"start_hole": 5, "players": ["노재호", "곽재영", "최성식"]},
}

st.title("⛳ 연세대 골프 대회 모바일 스코어보드")

# --- [3. 메뉴 선택] ---
menu = st.sidebar.radio("메뉴 선택", ["📝 스코어 입력", "🏆 실시간 리더보드", "⚙️ 운영진 설정"])

# ==========================================
# [메뉴 1] 스코어 입력 화면 (조별 / 상대 점수 입력)
# ==========================================
if menu == "📝 스코어 입력":
    st.header("📝 홀별 스코어 입력")
    
    group_name = st.selectbox("조 선택", list(GROUPS.keys()))
    group_info = GROUPS[group_name]
    start_hole = group_info["start_hole"]
    
    st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식 적용)")
    
    # 홀 선택 (시작 홀부터 순서대로 18홀 순환)
    hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
    selected_hole_idx = st.selectbox("입력할 홀 선택", range(18), format_func=lambda i: f"{i+1}번째 홀 (코스 {hole_sequence[i]}번 홀, Par {PAR_LIST[hole_sequence[i]-1]})")
    
    target_hole = hole_sequence[selected_hole_idx]
    par_val = PAR_LIST[target_hole - 1]
    
    st.subheader(f"📍 {selected_hole_idx + 1}번째 소화 중 (코스 {target_hole}번 홀 - Par {par_val})")
    
    with st.form(key="score_form"):
        player_inputs = {}
        for player in group_info["players"]:
            # 기존 입력값 불러오기 (기본값 파 대비 차이: 0 = Par)
            current_val = st.session_state.scores.get(player, {}).get(target_hole, 0)
            
            # -2(이글) ~ +2(더블보기 이상/더블파 제한) 상대 점수 입력
            score_diff = st.selectbox(
                f"{player} (기존 타수 대비)", 
                options=[-2, -1, 0, 1, 2], 
                index=current_val + 2,
                format_func=lambda x: "버디(-1)" if x==-1 else ("이글(-2)" if x==-2 else ("파(0)" if x==0 else f"+{x}")),
                key=f"{player}_{target_hole}"
            )
            player_inputs[player] = score_diff
            
        submitted = st.form_submit_button("💾 스코어 저장")
        if submitted:
            for player, diff in player_inputs.items():
                if player not in st.session_state.scores:
                    st.session_state.scores[player] = {}
                st.session_state.scores[player][target_hole] = diff
            st.success("성공적으로 저장되었습니다!")

# ==========================================
# [메뉴 2] 실시간 리더보드 (진행 홀 및 순위 표시)
# ==========================================
elif menu == "🏆 실시간 리더보드":
    st.header("🏆 실시간 리더보드")
    
    leaderboard_data = []
    for group_name, info in GROUPS.items():
        start_hole = info["start_hole"]
        hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
        
        for player in info["players"]:
            p_scores = st.session_state.scores.get(player, {})
            played_count = len(p_scores)
            
            # 총 타수 계산 (Par + 점수차)
            total_score = 0
            for h, diff in p_scores.items():
                total_score += (PAR_LIST[h-1] + diff)
                
            # 현재 치고 있는 홀 및 몇 번째 홀인지 계산
            if played_count > 0:
                current_nth_hole = played_count if played_count <= 18 else 18
                current_course_hole = hole_sequence[current_nth_hole - 1]
                status = f"{current_course_hole}번홀 ({current_nth_hole}번째)"
            else:
                status = "대기 중"
                
            leaderboard_data.append({
                "선수명": player,
                "조": group_name,
                "소화 홀 수": f"{played_count}/18",
                "현재 위치": status,
                "Gross 타수": total_score if played_count > 0 else "-"
            })
            
    df_lb = pd.DataFrame(leaderboard_data)
    st.dataframe(df_lb, use_container_width=True)

# ==========================================
# [메뉴 3] 운영진 설정
# ==========================================
elif menu == "⚙️ 운영진 설정":
    st.header("⚙️ 운영진 전용 관리 패널")
    st.text("조 편성 변경, 불참자 처리, 시작 홀 수정 기능이 제공되는 공간입니다.")