import streamlit as st
import pandas as pd

st.set_page_config(page_title="연세대 골프 대회 스코어보드", layout="centered", page_icon="⛳")

# --- 1. 실제 대회방식 시트에서 가져온 18홀 파(Par) 정보 ---
PAR_LIST = [4, 4, 3, 4, 5, 4, 3, 5, 4, 4, 3, 5, 4, 3, 5, 4, 4, 4]

# --- 2. 세션 상태 초기화 (스코어 데이터) ---
if 'scores' not in st.session_state:
    st.session_state.scores = {}  # {선수명: {홀번호: 타수차}}

# --- 3. 공유해주신 조편성 시트 기반 실제 선수단 데이터 ---
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
    
    hole_idx_key = f"current_hole_idx_{group_name}"
    if hole_idx_key not in st.session_state:
        st.session_state[hole_idx_key] = 0
        
    current_idx = st.session_state[hole_idx_key]
    current_course_hole = hole_sequence[current_idx]
    current_par = PAR_LIST[current_course_hole - 1]
    
    # 상단 네비게이션: 앞뒤 홀 이동 버튼
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
    
    # 앞뒤 홀 참고 디스플레이
    prev_h = hole_sequence[current_idx - 1] if current_idx > 0 else "-"
    next_h = hole_sequence[current_idx + 1] if current_idx < 17 else "-"
    st.caption(f"👀 [참고] 이전 홀(코스 {prev_h}번) ➔ **현재 입력 홀(코스 {current_course_hole}번, Par {current_par})** ➔ 다음 홀(코스 {next_h}번)")

    with st.form(key=f"unified_score_form_{group_name}_{current_idx}"):
        st.markdown(f"#### 🏌️‍♂️ {current_idx + 1}번째 홀 (코스 {current_course_hole}번홀, Par {current_par}) 스코어 입력")
        
        form_inputs = {}
        for player, p_data in players_info.items():
            if player not in st.session_state.scores:
                st.session_state.scores[player] = {}
                
            current_val = st.session_state.scores[player].get(current_course_hole, 0)
            
            # 더블파 맥스 제한 (파3: +3, 파4: +4, 파5: +5)
            max_over = current_par
            options = list(range(-2, max_over + 1))
            if current_val not in options:
                current_val = 0
                
            col_p1, col_p2 = st.columns([1, 2])
            with col_p1:
                st.markdown(f"**{player}**<br><span style='font-size:0.8em; color:gray;'>({p_data['dept']} / Hcap: {p_data['hcap']})</span>", unsafe_allow_html=True)
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
            st.write("")
            
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
        df_lb = df_lb.sort_values(by=["Sort_HasHcap", "Sort_Net"], ascending=[True, True])
        df_display = df_lb[["선수명", "Gross", "핸디캡", "Net", "소화홀/현재위치"]].reset_index(drop=True)
        df_display.index += 1
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없습니다.")

# ==========================================
# [메뉴 3] 운영진 관리
# ==========================================
elif menu == "⚙️ 운영진 관리":
    st.header("⚙️ 운영진 관리 패널")
    st.markdown("조편성 시트 데이터 기반 등록 현황입니다.")
    
    for group_name, info in st.session_state.groups.items():
        with st.expander(f"조: {group_name} (시작홀: {info['start_hole']}번)"):
            for p, d in info["players"].items():
                st.text(f"- {p} ({d['dept']} / 핸디캡: {d['hcap']})")