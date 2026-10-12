import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="연세대 골프 대회 스코어보드", layout="centered", page_icon="⛳")

# 15초마다 자동 새로고침 (모든 기기에서 실시간 동기화 유지)
st_autorefresh(interval=15000, key="datarefresh")

# 모바일 컴팩트 스타일링 CSS
st.markdown("""
<style>
.stSelectbox div[data-baseweb="select"] {
    min-height: 35px;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 코스 파(Par) 정보 ---
PAR_LIST = [4, 4, 3, 4, 5, 4, 3, 5, 4, 4, 3, 5, 4, 3, 5, 4, 4, 4]

# --- 2. 구글 시트 연결 (ttl=0으로 설정하여 캐시 없이 실시간 최신 데이터 로드) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 구글 시트에서 점수 데이터 읽어오기 (ttl=0 필수: 실시간 반영을 위해 캐시 방지)
    df_scores_db = conn.read(worksheet="Scores", ttl=0)
    
    # 불러온 DB 데이터를 앱 내 세션(scores) 구조로 매핑
    if 'scores' not in st.session_state:
        st.session_state.scores = {}
        if not df_scores_db.empty and all(col in df_scores_db.columns for col in ["선수명", "홀번호", "점수차"]):
            for _, row in df_scores_db.iterrows():
                p_name = str(row["선수명"])
                h_num = int(row["홀번호"])
                diff_val = int(row["점수차"])
                if p_name not in st.session_state.scores:
                    st.session_state.scores[p_name] = {}
                st.session_state.scores[p_name][h_num] = diff_val
except Exception as e:
    st.warning(f"구글 시트 연동 중이거나 데이터를 읽어오는 중입니다. (기본 모드 작동)")
    if 'scores' not in st.session_state:
        st.session_state.scores = {}

# --- 3. 조편성 데이터 ---
if 'groups' not in st.session_state:
    st.session_state.groups = {
        "1A조": {
            "start_hole": 1,
            "players": {
                "노재호": {"hcap": 21.0, "dept": "세라믹"},
                "곽재영": {"hcap": 22.0, "dept": "전자"},
                "박주원": {"hcap": 15.0, "dept": "전자"}
            }
        },
        "1B조": {
            "start_hole": 1,
            "players": {
                "이용일": {"hcap": 25.0, "dept": "토목"},
                "신성원": {"hcap": 14.0, "dept": "전기"},
                "신현경": {"hcap": 17.0, "dept": "전자"},
                "이창호": {"hcap": 23.0, "dept": "전기"}
            }
        },
        "2조": {
            "start_hole": 2,
            "players": {
                "마이클 안": {"hcap": 8.0, "dept": "국제학부"},
                "양진기": {"hcap": "NA", "dept": "전산"},
                "박종화": {"hcap": 10.0, "dept": "전산"},
                "김택규": {"hcap": 13.0, "dept": "생화학"}
            }
        },
        "3A조": {
            "start_hole": 3,
            "players": {
                "김은혁": {"hcap": 23.0, "dept": "의학"},
                "변원석": {"hcap": "NA", "dept": "기계"},
                "임봉욱": {"hcap": 17.0, "dept": "건축"},
                "이은홍": {"hcap": 25.0, "dept": "건축"}
            }
        },
        "3B조": {
            "start_hole": 3,
            "players": {
                "남명현": {"hcap": 25.0, "dept": "수학"},
                "박재효": {"hcap": 34.0, "dept": "경제"},
                "우규진": {"hcap": 18.0, "dept": "전자"},
                "이미나": {"hcap": 24.0, "dept": "영문"}
            }
        },
        "4조": {
            "start_hole": 4,
            "players": {
                "임주연": {"hcap": "NA", "dept": "세라믹"},
                "황경진": {"hcap": "NA", "dept": "금속"},
                "김윤경": {"hcap": 36.0, "dept": "-"}
            }
        },
        "5A조": {
            "start_hole": 5,
            "players": {
                "이동휘": {"hcap": "NA", "dept": "금속"},
                "양성흠": {"hcap": "NA", "dept": "-"},
                "신재원": {"hcap": "NA", "dept": "전자"},
                "송창걸": {"hcap": 14.0, "dept": "기계"}
            }
        },
        "5B조": {
            "start_hole": 5,
            "players": {
                "박준식": {"hcap": 11.0, "dept": "사체"},
                "정태양": {"hcap": "NA", "dept": "스포츠레저"},
                "최성식": {"hcap": 13.0, "dept": "생명공학"},
                "김용민": {"hcap": 5.0, "dept": "전기"}
            }
        }
    }

st.title("⛳ 연세대 골프 대회 모바일 스코어보드")
st.markdown("---")

menu = st.sidebar.radio("메뉴 선택", ["📝 스코어 입력", "🏆 실시간 리더보드", "⚙️ 운영진 관리"])

# ==========================================
# [메뉴 1] 스코어 입력
# ==========================================
if menu == "📝 스코어 입력":
    st.header("📝 홀별 스코어 입력")
    
    group_list = list(st.session_state.groups.keys())
    group_name = st.selectbox("조 선택", group_list)
    group_info = st.session_state.groups[group_name]
    start_hole = group_info["start_hole"]
    players_info = group_info["players"]
    
    st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식)")
    
    hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
    
    hole_idx_key = f"current_hole_idx_{group_name}"
    if hole_idx_key not in st.session_state:
        st.session_state[hole_idx_key] = 0
        
    current_idx = st.session_state[hole_idx_key]
    current_course_hole = hole_sequence[current_idx]
    current_par = PAR_LIST[current_course_hole - 1]
    
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

    with st.form(key=f"unified_score_form_{group_name}_{current_idx}"):
        st.markdown(f"#### 🏌️‍♂️ Hole {current_course_hole}, Par {current_par}")
        
        form_inputs = {}
        for player in players_info.keys():
            if player not in st.session_state.scores:
                st.session_state.scores[player] = {}
                
            current_val = st.session_state.scores[player].get(current_course_hole, 0)
            
            max_over = current_par
            options = list(range(-2, max_over + 1))
            if current_val not in options:
                current_val = 0
                
            col_name, col_select = st.columns([1.5, 2.5])
            with col_name:
                st.markdown(f"<div style='padding-top: 6px; font-weight: bold; font-size: 0.95rem;'>{player}</div>", unsafe_allow_html=True)
            with col_select:
                score_diff = st.selectbox(
                    f"{player} 성적",
                    options=options,
                    index=options.index(current_val) if current_val in options else 2,
                    format_func=lambda x: "이글(-2)" if x==-2 else ("버디(-1)" if x==-1 else ("파(0)" if x==0 else f"+{x}")),
                    key=f"input_{player}_{current_course_hole}",
                    label_visibility="collapsed"
                )
                form_inputs[player] = score_diff
            
        submitted = st.form_submit_button("💾 이 홀의 스코어 저장 및 다음 홀로 ➔")
        if submitted:
            for player, diff in form_inputs.items():
                st.session_state.scores[player][current_course_hole] = diff
            
            # 구글 시트 'Scores' 탭에 전체 점수 상태를 통째로 업데이트하는 로직
            try:
                all_scores_list = []
                for p, holes in st.session_state.scores.items():
                    for h, d in holes.items():
                        all_scores_list.append({"선수명": p, "홀번호": h, "점수차": d})
                df_to_save = pd.DataFrame(all_scores_list)
                conn.update(worksheet="Scores", data=df_to_save)
            except Exception as e:
                st.error(f"구글 시트 저장 실패: {e}")
            
            st.session_state[hole_idx_key] = (current_idx + 1) % 18
            st.success("저장 완료! 구글 시트 동기화 및 다음 홀로 이동합니다.")
            st.rerun()

    # 최근 입력 홀 기록 테이블
    st.markdown("---")
    st.markdown("📋 **[최근 입력된 홀 기록]**")
    
    start_history_idx = max(0, current_idx - 2)
    history_indices = list(range(start_history_idx, current_idx + 1))
    
    history_table_rows = []
    for player in players_info.keys():
        row_data = {"선수명": player}
        p_scores = st.session_state.scores.get(player, {})
        for idx in history_indices:
            h_num = hole_sequence[idx]
            h_str = str(h_num)
            if h_num in p_scores:
                diff = p_scores[h_num]
                row_data[h_str] = "0" if diff==0 else (f"버디({diff})" if diff==-1 else (f"이글({diff})" if diff==-2 else f"+{diff}"))
            else:
                row_data[h_str] = "-"
        history_table_rows.append(row_data)
        
    if history_table_rows:
        df_history = pd.DataFrame(history_table_rows)
        cols = ["선수명"] + [str(hole_sequence[idx]) for idx in history_indices]
        df_history = df_history[cols]
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.caption("아직 기록된 점수가 없습니다.")

# ==========================================
# [메뉴 2] 실시간 리더보드
# ==========================================
elif menu == "🏆 실시간 리더보드":
    st.header("🏆 실시간 리더보드 (Net 순위)")
    st.caption("🔄 구글 시트와 연동되어 실시간으로 자동 동기화됩니다.")
    
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
            
            if played_count > 0 and has_hcap:
                net_val = round(gross_total - float(hcap))
                net_score = str(net_val)
            else:
                net_score = "-"
                
            if has_hcap:
                display_hcap = str(int(round(float(hcap))))
            else:
                display_hcap = "NA"
                
            if played_count == 0:
                current_pos = "0"
            elif played_count >= 18:
                current_pos = "F"
            else:
                last_played_idx = played_count - 1
                current_pos = str(hole_sequence[last_played_idx])
                
            leaderboard_data.append({
                "선수명": player,
                "핸디캡": display_hcap,
                "Gross": str(gross_total) if played_count > 0 else "-",
                "Net": net_score,
                "시작홀": str(start_hole),
                "현재위치": current_pos,
                "Sort_HasHcap": 0 if has_hcap else 1,
                "Sort_Net": float(net_score) if net_score != "-" else 999
            })
            
    df_lb = pd.DataFrame(leaderboard_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by=["Sort_HasHcap", "Sort_Net"], ascending=[True, True])
        df_display = df_lb[["선수명", "핸디캡", "Gross", "Net", "시작홀", "현재위치"]].reset_index(drop=True)
        df_display.index += 1
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없습니다.")

# ==========================================
# [메뉴 3] 운영진 관리
# ==========================================
elif menu == "⚙️ 운영진 관리":
    st.header("⚙️ 운영진 전용 관리 패널")
    
    admin_password = st.text_input("운영진 비밀번호를 입력하세요", type="password")
    CORRECT_PASSWORD = "yonsei2026"
    
    if admin_password == CORRECT_PASSWORD:
        st.success("인증되었습니다.")
    elif admin_password != "":
        st.error("비밀번호가 틀렸습니다.")
