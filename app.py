import streamlit as st
import pandas as pd

st.set_page_config(page_title="연세대 골프 대회 스코어보드", layout="centered", page_icon="⛳")

# --- 1. 코스 파(Par) 정보 (공유해주신 실제 18홀 파 정보) ---
# 총 72 파 구성: 4, 4, 4, 3, 4, 5, 3, 5, 4, 4, 5, 3, 4, 4, 3, 5, 4, 4
PAR_LIST = [4, 4, 4, 3, 4, 5, 3, 5, 4, 4, 5, 3, 4, 4, 3, 5, 4, 4]

# --- 2. 세션 상태 초기화 (조편성 및 점수 데이터 관리) ---
if 'scores' not in st.session_state:
    st.session_state.scores = {}  # {선수명: {코스홀번호: 타수차}}

# 초기 조편성 및 핸디캡 데이터 (운영진이 앱 내에서 실시간 수정 가능하도록 세션에 저장)
if 'groups' not in st.session_state:
    st.session_state.groups = {
        "1A조": {
            "start_hole": 1,
            "players": {"김은혁": 23.0, "이은홍": 25.0, "박주원": "NA"}
        },
        "5A조": {
            "start_hole": 5,
            "players": {"노재호": 21.0, "곽재영": 12.5, "최성식": "NA"}
        },
        "10B조": {
            "start_hole": 10,
            "players": {"김태규": 5.0, "허형회": "NA", "임봉욱": 18.2}
        }
    }

st.title("⛳ 연세대 골프 대회 모바일 스코어보드")
st.markdown("---")

# --- 네비게이션 메뉴 ---
menu = st.sidebar.radio("메뉴 선택", ["📝 스코어 입력", "🏆 실시간 리더보드", "⚙️ 운영진 관리 (조편성 수정)"])

# ==========================================
# [메뉴 1] 홀별 스코어 입력 (3홀씩 노출 + 앞뒤 이동 + 맥스 더블파 제한)
# ==========================================
if menu == "📝 스코어 입력":
    st.header("📝 홀별 스코어 입력")
    
    group_list = list(st.session_state.groups.keys())
    if not group_list:
        st.warning("등록된 조가 없습니다. 운영진 관리 메뉴에서 조를 먼저 설정해 주세요.")
    else:
        group_name = st.selectbox("조 선택", group_list)
        group_info = st.session_state.groups[group_name]
        start_hole = group_info["start_hole"]
        players_dict = group_info["players"]
        
        st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식)")
        
        if not players_dict:
            st.warning("이 조에 편성된 선수가 없습니다.")
        else:
            # 시작 홀부터 순서대로 18홀 순환 시퀀스 생성
            hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
            
            page_key = f"page_{group_name}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 0  # 3홀씩 총 6페이지 (0~5)
                
            # 앞뒤 이동 버튼
            col_prev, col_mid, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("◀ 이전 홀들") and st.session_state[page_key] > 0:
                    st.session_state[page_key] -= 1
                    st.rerun()
            with col_mid:
                st.markdown(f"<div style='text-align: center;'><b>구간 {st.session_state[page_key] + 1} / 6</b></div>", unsafe_allow_html=True)
            with col_next:
                if st.button("다음 홀들 ▶") and st.session_state[page_key] < 5:
                    st.session_state[page_key] += 1
                    st.rerun()
                    
            current_page = st.session_state[page_key]
            chunk_start = current_page * 3
            chunk_end = min(chunk_start + 3, 18)
            displayed_indices = range(chunk_start, chunk_end)
            
            st.markdown(f"**[현재 입력 구간: {chunk_start + 1}번째 ~ {chunk_end}번째 홀]**")
            
            with st.form(key=f"score_form_{group_name}_{current_page}"):
                player_inputs = {}
                
                for player in players_dict.keys():
                    st.markdown(f"#### 👤 {player}")
                    if player not in st.session_state.scores:
                        st.session_state.scores[player] = {}
                        
                    for idx in displayed_indices:
                        course_hole = hole_sequence[idx]
                        par_val = PAR_LIST[course_hole - 1]
                        
                        # 더블파 맥스 제한 (파3는 +3, 파4는 +4, 파5는 +5까지)
                        max_over = par_val
                        options = list(range(-2, max_over + 1))  # -2(이글) ~ 더블파(+Par)
                        
                        current_val = st.session_state.scores[player].get(course_hole, 0)
                        if current_val not in options:
                            current_val = 0
                            
                        score_diff = st.selectbox(
                            f"{idx+1}번째 홀 (코스 {course_hole}번, Par {par_val})",
                            options=options,
                            index=options.index(current_val) if current_val in options else 2,
                            format_func=lambda x: "이글(-2)" if x==-2 else ("버디(-1)" if x==-1 else ("파(0)" if x==0 else f"+{x}")),
                            key=f"{player}_hole_{course_hole}"
                        )
                        player_inputs[(player, course_hole)] = score_diff
                    st.markdown("---")
                    
                submitted = st.form_submit_button("💾 현재 구간 스코어 저장하기")
                if submitted:
                    for (player, course_hole), diff in player_inputs.items():
                        st.session_state.scores[player][course_hole] = diff
                    st.success("스코어가 성공적으로 저장되었습니다!")

# ==========================================
# [메뉴 2] 실시간 리더보드 (Net 순위 중심, NA 선수 하단 정렬)
# ==========================================
elif menu == "🏆 실시간 리더보드":
    st.header("🏆 실시간 리더보드 (Net 순위)")
    
    leaderboard_data = []
    all_players_info = []
    
    for group_name, info in st.session_state.groups.items():
        start_hole = info["start_hole"]
        hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
        for player, hcap in info["players"].items():
            all_players_info.append((player, hcap, start_hole, hole_sequence))
            
    for player, hcap, start_hole, hole_sequence in all_players_info:
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
        df_display.index += 1  # 1위부터 순위 표시
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없습니다.")

# ==========================================
# [메뉴 3] 운영진 관리 (당일 조편성 변경 및 선수 수정)
# ==========================================
elif menu == "⚙️ 운영진 관리 (조편성 수정)":
    st.header("⚙️ 운영진 당일 조편성 관리 패널")
    st.markdown("경기 당일 불참자 발생, 선수 이동, 시작 홀 변경 등을 실시간으로 수정할 수 있습니다.")
    
    st.subheader("📋 현재 조편성 현황 및 수정")
    
    # 조별로 펼쳐서 수정할 수 있도록 구성
    groups_to_delete = []
    for group_name, info in list(st.session_state.groups.items()):
        with st.expander(f"조 이름: {group_name} (시작 홀: {info['start_hole']}번)"):
            new_start_hole = st.number_input(f"시작 홀 변경 ({group_name})", min_value=1, max_value=18, value=int(info['start_hole']), key=f"sh_{group_name}")
            st.session_state.groups[group_name]['start_hole'] = new_start_hole
            
            st.markdown("**소속 선수 및 핸디캡**")
            players_to_delete = []
            for player, hcap in list(info['players'].items()):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    new_name = st.text_input("선수명", value=player, key=f"pname_{group_name}_{player}")
                with col2:
                    new_hcap = st.text_input("핸디캡 (숫자 또는 NA)", value=str(hcap), key=f"phcap_{group_name}_{player}")
                with col3:
                    if st.button("삭제", key=f"del_p_{group_name}_{player}"):
                        players_to_delete.append(player)
                        
                # 이름이나 핸디캡 변경 반영 로직
                if new_name != player and new_name not in st.session_state.groups[group_name]['players']:
                    st.session_state.groups[group_name]['players'][new_name] = st.session_state.groups[group_name]['players'].pop(player)
                    player = new_name
                try:
                    if new_hcap.upper() == "NA":
                        st.session_state.groups[group_name]['players'][player] = "NA"
                    else:
                        st.session_state.groups[group_name]['players'][player] = float(new_hcap)
                except ValueError:
                    pass
                    
            for p in players_to_delete:
                del st.session_state.groups[group_name]['players'][p]
                st.rerun()
                
            # 선수 추가 폼
            with st.form(key=f"add_player_{group_name}"):
                col_ap1, col_ap2, col_ap3 = st.columns([2, 2, 1])
                with col_ap1:
                    add_name = st.text_input("추가할 선수명")
                with col_ap2:
                    add_hcap = st.text_input("핸디캡 (숫자 또는 NA)", value="NA")
                with col_ap3:
                    add_btn = st.form_submit_button("선수 추가")
                if add_btn and add_name:
                    st.session_state.groups[group_name]['players'][add_name] = float(add_hcap) if add_hcap.upper()!="NA" else "NA"
                    st.success(f"{add_name} 선수가 추가되었습니다!")
                    st.rerun()
                    
            if st.button(f"🗑️ '{group_name}' 조 전체 삭제", key=f"del_g_{group_name}"):
                groups_to_delete.append(group_name)
                
    for g in groups_to_delete:
        del st.session_state.groups[g]
        st.rerun()
        
    st.markdown("---")
    st.subheader("➕ 새 조 추가하기")
    with st.form(key="add_group_form"):
        new_g_name = st.text_input("새 조 이름 (예: 6A조)")
        new_g_start = st.number_input("시작 홀", min_value=1, max_value=18, value=1)
        add_g_btn = st.form_submit_button("조 생성하기")
        if add_g_btn and new_g_name:
            if new_g_name not in st.session_state.groups:
                st.session_state.groups[new_g_name] = {"start_hole": int(new_g_start), "players": {}}
                st.success(f"'{new_g_name}' 조가 생성되었습니다!")
                st.rerun()
            else:
                st.error("이미 존재하는 조 이름입니다.")