import streamlit as st
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime
import re
from collections import Counter
import json

# 환경변수 로드
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")
DB_PATH = "./child_edu_ai.db"

# DB 유틸 함수
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT,
            pw TEXT,
            grade INTEGER,
            semester INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id TEXT,
            lesson_id TEXT,
            date TEXT,
            title TEXT,
            content TEXT,
            materials_text TEXT,
            feedback TEXT,
            PRIMARY KEY (id, lesson_id)
        )
    """)
    conn.commit()
init_db()

# DB 연동 함수
def add_account(id, name, pw, grade, semester):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO accounts (id, name, pw, grade, semester) VALUES (?, ?, ?, ?, ?)", (id, name, pw, grade, semester))
    conn.commit()

def get_account(id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, pw, grade, semester FROM accounts WHERE id=?", (id,))
    row = c.fetchone()
    if row:
        return {"id": row[0], "name": row[1], "pw": row[2], "grade": row[3], "semester": row[4]}
    return None

def add_history(id, lesson_id, date, title, content, materials_text, feedback=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO history (id, lesson_id, date, title, content, materials_text, feedback)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (id, lesson_id, date, title, content, materials_text, feedback))
    conn.commit()

def get_history(id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT lesson_id, date, title, content, materials_text, feedback FROM history WHERE id=? ORDER BY date DESC", (id,))
    rows = c.fetchall()
    return [
        {"lesson_id": r[0], "date": r[1], "title": r[2], "content": r[3], "materials_text": r[4], "feedback": r[5]}
        for r in rows
    ]

def update_feedback(id, lesson_id, feedback):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE history SET feedback=? WHERE id=? AND lesson_id=?", (feedback, id, lesson_id))
    conn.commit()

def setup_ui_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
        html, body, [class*="css"]  { font-family: 'Jua', sans-serif; }
        :root { color-scheme: light !important; }
        html, body, .stApp { color: #0b1220 !important; }
        /* 밝고 산뜻한 배경 */
        .stApp { background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%); }
        /* 사이드바 밝은 하늘색 테마 */
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #e0f2fe 0%, #b3e5fc 100%) !important; border-right: 1px solid #81d4fa; }
        [data-testid="stSidebar"] * { color: #0b1220 !important; }
        /* 기본 텍스트/링크 색상 보정 */
        .stMarkdown, .stMarkdown p, .stMarkdown li, a { color: #0b1220 !important; }
        
        /* 라디오 버튼 선택지 텍스트 색상 */
        .stRadio > div { color: #0b1220 !important; }
        .stRadio > div > label { color: #0b1220 !important; }
        .stRadio > div > label > div { color: #0b1220 !important; }
        .stRadio label span { color: #0b1220 !important; }
        
        /* 버튼 색상 조정 - 밝은 회색 톤 */
        .stButton > button { 
            background-color: #e2e8f0 !important; 
            color: #1e293b !important; 
            border: 1px solid #cbd5e1 !important;
            font-weight: 600 !important;
        }
        .stButton > button:hover { 
            background-color: #cbd5e1 !important; 
            color: #0f172a !important; 
        }
        
        /* 사이드바 Primary 버튼 (새 학습지 생성) */
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] { 
            background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%) !important;
            border: 2px solid #86efac !important;
            border-radius: 14px !important;
            color: #166534 !important;
            font-weight: 700 !important;
            padding: 12px 16px !important;
            width: 100% !important;
            font-size: 1rem !important;
            margin-top: 12px !important;
        }
        
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"]:hover { 
            background: linear-gradient(135deg, #bbf7d0 0%, #86efac 100%) !important;
            border-color: #4ade80 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(134, 239, 172, 0.3) !important;
        }
        
        /* 사이드바 셀렉트박스 스타일링 */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #fff7ed !important; /* 연한 오렌지 */
            border: 2px solid #fed7aa !important; /* 파스텔 오렌지 테두리 */
            border-radius: 12px !important;
            color: #9a3412 !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox > div > div:focus {
            border-color: #fb923c !important; /* 포커스시 오렌지 */
            box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.2) !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox label {
            color: #334155 !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
        }
        
        /* 드롭다운 메뉴 스타일링 */
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
            background-color: #fff7ed !important;
            border: 2px solid #fed7aa !important;
            border-radius: 12px !important;
        }
        
        /* 선택된 옵션 텍스트 */
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] [role="option"] {
            color: #9a3412 !important;
            font-weight: 600 !important;
        }
        
        /* 호버 효과 */
        [data-testid="stSidebar"] .stSelectbox > div > div:hover {
            border-color: #fb923c !important;
            background-color: #ffedd5 !important;
        }
        
        /* 드롭다운 리스트 스타일링 */
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="menu"] {
            background-color: #fff7ed !important;
            border: 2px solid #fed7aa !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(251, 146, 60, 0.15) !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="menu"] [role="option"] {
            background-color: transparent !important;
            color: #9a3412 !important;
            font-weight: 600 !important;
            padding: 8px 12px !important;
            border-radius: 8px !important;
            margin: 2px 4px !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="menu"] [role="option"]:hover {
            background-color: #ffedd5 !important;
            color: #ea580c !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="menu"] [aria-selected="true"] {
            background-color: #fed7aa !important;
            color: #9a3412 !important;
            font-weight: 700 !important;
        }
        
        /* 사이드바 텍스트 입력(추가 요청) 라벨 스타일 */
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stTextArea label {
            color: #334155 !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            margin-bottom: 6px !important;
        }
        /* 단일행 인풋과 텍스트영역 모두 동일 룩앤필 */
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stTextArea textarea,
        [data-testid="stSidebar"] textarea {
            background-color: #fff7ed !important; /* 연한 오렌지 */
            border: 2px solid #fed7aa !important;   /* 파스텔 오렌지 테두리 */
            border-radius: 12px !important;
            color: #0b1220 !important;
            font-weight: 600 !important;
            padding: 10px 12px !important;
            width: 100% !important;
            box-shadow: none !important; /* 검정 테두리 제거 */
            outline: none !important;
        }
        [data-testid="stSidebar"] .stTextArea textarea {
            min-height: 64px !important; /* 기본 두 줄 높이 */
            line-height: 1.4 !important;
            resize: none !important; /* 크기 고정 */
        }
        [data-testid="stSidebar"] .stTextInput input::placeholder,
        [data-testid="stSidebar"] .stTextArea textarea::placeholder {
            color: rgba(154, 52, 18, 0.65) !important;
        }
        [data-testid="stSidebar"] .stTextInput input:focus,
        [data-testid="stSidebar"] .stTextArea textarea:focus {
            border-color: #fb923c !important; /* 포커스시 오렌지 */
            box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.2) !important;
            outline: none !important;
        }
        
        /* 사이드바 학생 정보 카드 */
        .sidebar-student-card {
            background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
            border: 2px solid #4dd0e1;
            border-radius: 16px;
            padding: 16px;
            margin: 0 0 20px 0;
            text-align: center;
            box-shadow: 0 4px 12px rgba(77, 208, 225, 0.15);
        }
        
        .student-name {
            font-size: 1.1rem;
            font-weight: 800;
            color: #006064;
            margin-bottom: 4px;
        }
        
        .student-grade {
            font-size: 0.9rem;
            font-weight: 600;
            color: #00838f;
            opacity: 0.8;
        }
        
        /* 사이드바 섹션 */
        .sidebar-section {
            margin: 20px 0 12px 0;
        }
        
        .sidebar-section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #334155;
            padding: 12px 0 8px 0;
            border-bottom: 2px solid #e2e8f0;
            margin-bottom: 12px;
        }
        
        /* 학습 이력 메타 정보 */
        .history-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: -8px 0 12px 0;
            padding: 0 4px;
            font-size: 0.85rem;
        }
        
        .history-meta .history-score {
            background: linear-gradient(135deg, #fff4db 0%, #fef3c7 100%);
            color: #92400e;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.8rem;
        }
        
        .history-meta .history-date {
            color: #64748b;
            font-weight: 500;
            font-size: 0.8rem;
        }
        
        /* 사이드바 버튼 (이력 항목) 스타일링 */
        /* 사이드바 이력 버튼: 밝은 배경, 진한 글자, 고정 높이 (강제 덮어쓰기) */
        [data-testid="stSidebar"] .stButton > button,
        [data-testid="stSidebar"] button,
        [data-testid="stSidebar"] [data-baseweb="button"],
        [data-testid="stSidebar"] [role="button"] {
            background-color: #f5f7fb !important;
            background-image: none !important;
            border: 2px solid #e5e7eb !important;
            border-radius: 12px !important;
            color: #0b1220 !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            padding: 10px 14px !important;
            width: 100% !important;
            text-align: left !important;
            margin-bottom: 10px !important;
            height: 56px !important;
            line-height: 34px !important; /* 높이 내에서 수직 중앙 느낌 */
            display: block !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }

        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] button:hover,
        [data-testid="stSidebar"] [data-baseweb="button"]:hover,
        [data-testid="stSidebar"] [role="button"]:hover {
            background-color: #eef2f7 !important;
            border-color: #cbd5e1 !important;
            color: #0b1220 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(148, 163, 184, 0.18) !important;
        }

        [data-testid="stSidebar"] .stButton > button:focus,
        [data-testid="stSidebar"] button:focus,
        [data-testid="stSidebar"] [data-baseweb="button"]:focus,
        [data-testid="stSidebar"] [role="button"]:focus {
            outline: none !important;
            border-color: #94a3b8 !important;
            box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.25) !important;
        }
        .worksheet-title { font-size: 1.22rem; font-weight: 700; margin: 0.2rem 0 0.9rem 0; color: #0f172a; }
        .problem-card {
            padding: 16px 18px; border-radius: 14px; margin: 12px 0; border: 1px solid #e9eef5;
            background: #ffffff;
            box-shadow: 0 6px 14px rgba(31, 64, 132, 0.06);
        }
        .problem-header { font-size: 1.12rem; font-weight: 800; color: #1f2a44; margin-bottom: 8px; }
        .problem-text { font-size: 1.05rem; line-height: 1.7; color: #0b1220; }
        .answer-label { font-size: 1.0rem; font-weight: 700; color: #10b981; margin: 6px 0 4px 2px; }
        .hint { font-size: 0.95rem; color: #64748b; }
        .stTextInput>div>div>input { font-size: 1.05rem; padding: 10px 12px; border-radius: 10px; }
        table.perq { width: 100%; border-collapse: collapse; }
        table.perq th, table.perq td { padding: 10px 12px; border-bottom: 1px solid #edf2f7; text-align: left; font-size: 1.0rem; }
        table.perq th { background: #f1f5ff; color: #0f172a; font-weight: 800; }
        .chip { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #eaf2ff; color: #194185; font-weight: 800; font-size: 0.95rem; }
        .badge-ok { display:inline-block; padding: 6px 12px; border-radius: 10px; background: #d1fae5; color: #065f46; font-weight: 900; }
        .badge-x  { display:inline-block; padding: 6px 12px; border-radius: 10px; background: #ffe1e1; color: #991b1b; font-weight: 900; }
        /* 이력 아이템 */
        .history-item { padding: 10px 12px; border-radius: 12px; border: 1px solid #e9eef5; background: #ffffff; box-shadow: 0 3px 10px rgba(31,64,132,0.04); margin-bottom: 10px; }
        .history-title { font-size: 1.0rem; color: #0b1220; font-weight: 800; margin-bottom: 6px; }
        .history-row { display:flex; align-items:center; gap:10px; }
        .history-score { display:inline-block; padding: 4px 10px; border-radius: 999px; background: #fff4db; color: #9a3412; font-weight: 900; }
        .history-date { color: #94a3b8; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_per_question_table(perq_text: str) -> str:
    import re as _re
    rows = []
    for line in perq_text.splitlines():
        line = line.strip()
        m = _re.match(r"(\d+)\)\s*학생:\s*\(([ABCD\-])\)\s*\|\s*정답:\s*\(([ABCD\-])\)\s*\|\s*채점:\s*(O|X)", line)
        if m:
            n = m.group(1)
            stu = m.group(2)
            corr = m.group(3)
            ox = m.group(4)
            rows.append((n, stu, corr, ox))
    if not rows:
        return ""
    # Build HTML table
    parts = ["<table class='perq'>",
             "<thead><tr><th>문항</th><th>학생 답</th><th>정답</th><th>채점</th></tr></thead>",
             "<tbody>"]
    for (n, stu, corr, ox) in rows:
        badge = f"<span class='badge-ok'>O</span>" if ox == 'O' else f"<span class='badge-x'>X</span>"
        parts.append(
            f"<tr><td>{n}번</td><td><span class='chip'>{stu}</span></td><td><span class='chip'>{corr}</span></td><td>{badge}</td></tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)

def parse_worksheet(materials_text: str):
    # [Worksheet] 부분만 추출
    text = materials_text
    if "[Worksheet]" in materials_text:
        text = materials_text.split("[Worksheet]")[-1]
    if "[AnswerKey]" in text:
        text = text.split("[AnswerKey]")[0]

    # [Problem N] 기준으로 분리
    import re as _re
    problem_pattern = _re.compile(r"\[Problem\s*(\d+)\]\s*", _re.IGNORECASE)
    parts = list(problem_pattern.finditer(text))
    problems = []
    for idx, match in enumerate(parts):
        start = match.end()
        end = parts[idx + 1].start() if idx + 1 < len(parts) else len(text)
        raw = text[start:end].strip()
        # [Answer]와 [Explanation] 제거
        raw = raw.split("[Answer]")[0].strip()
        raw = raw.split("[Explanation]")[0].strip()
        # Choices 파싱
        stem = raw
        choices_block = ""
        if "Choices:" in raw:
            parts2 = raw.split("Choices:", 1)
            stem = parts2[0].strip()
            choices_block = parts2[1]
        # A)~D) 추출
        choice_map = {}
        for label in ["A", "B", "C", "D"]:
            m = _re.search(rf"\b{label}\)\s*(.+)", choices_block)
            if m:
                choice_map[label] = m.group(1).strip()
        number = int(match.group(1)) if match.group(1).isdigit() else (idx + 1)
        if stem:
            problems.append({"number": number, "text": stem, "choices": choice_map})
    return problems

def remove_markdown_links(text):
    # [텍스트](링크) → 텍스트
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # [텍스트] → 텍스트
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)
    return text

def load_curriculum_subjects(grade, semester):
    """특정 학년/학기의 커리큘럼 subjects 로드"""
    try:
        with open("resource/curriculum.json", "r", encoding="utf-8") as f:
            curriculum_data = json.load(f)
        
        for item in curriculum_data:
            if item.get("grade") == grade and item.get("semester") == semester:
                return item.get("subjects", [])
        
        return []
    except Exception as e:
        st.error(f"커리큘럼 데이터 로드 실패: {e}")
        return []

def get_history_for_feedback(history):
    result = []
    for item in history:
        # content에서 주제 추출
        topic = item['content'].split('\n')[0][:30] if item['content'] else ""
        feedback = item.get('feedback', '') or ""  # None/null을 빈 문자열로 보정
        result.append({
            "topic": topic,
            "feedback": feedback
        })
    return result

def render_overall_feedback(history):
    # 학습 주제, 피드백 요약 추출
    topics = []
    feedbacks = []
    for item in history:
        # 학습 주제(lesson content의 첫 줄)
        if item['content']:
            topic_line = item['content'].split('\n')[0][:30]
            topics.append(remove_markdown_links(topic_line))
        # 피드백
        if item.get('feedback'):
            feedbacks.append(remove_markdown_links(item['feedback']))
    topic_cnt = Counter(topics)
    # 피드백 요약(가장 많이 등장하는 단어)
    feedback_text = ' '.join(feedbacks)
    words = [w for w in re.findall(r'\w+', feedback_text) if len(w) > 1]
    word_cnt = Counter(words)
    common_words = ', '.join([w for w, _ in word_cnt.most_common(3)])
    
    # 마크다운 종합 피드백
    md = [
        "# 📊 나의 학습 분석\n",
        f"- **학습 주제:** " + ', '.join([f"{k}({v}회)" for k, v in topic_cnt.most_common()]) if topic_cnt else "- **학습 주제:** 없음",
        f"- **AI 피드백 요약:** {common_words if common_words else '아직 피드백이 충분하지 않아요!'}\n",
        "## 📝 앞으로 이런 학습을 추천해요!",
        "- 꾸준히 문제를 풀며 다양한 유형에 익숙해져 보세요.",
    ]
    return '\n'.join(md)

# 세션 상태 최소화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "child_id" not in st.session_state:
    st.session_state.child_id = None
if "child_name" not in st.session_state:
    st.session_state.child_name = None
if "child_pw" not in st.session_state:
    st.session_state.child_pw = None
if "child_grade" not in st.session_state:
    st.session_state.child_grade = None
if "child_semester" not in st.session_state:
    st.session_state.child_semester = None
if "selected_lesson" not in st.session_state:
    st.session_state.selected_lesson = None
if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "show_register" not in st.session_state:
    st.session_state.show_register = False
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "overall_feedback_text" not in st.session_state:
    st.session_state.overall_feedback_text = None
if "overall_feedback_needed" not in st.session_state:
    st.session_state.overall_feedback_needed = False

# 쿼리 파라미터로 동작 제어
action = st.query_params.get("action", "")

if action == "login":
    st.session_state.show_login = True
    st.session_state.show_register = False
elif action == "register":
    st.session_state.show_register = True
    st.session_state.show_login = False
elif action == "logout":
    st.session_state.logged_in = False
    st.session_state.child_id = None
    st.session_state.child_name = None
    st.session_state.child_pw = None
    st.session_state.child_grade = None
    st.session_state.child_semester = None
    st.session_state.selected_lesson = None
    st.session_state.overall_feedback_text = None
    st.session_state.overall_feedback_needed = False
    st.rerun()

# 앱 타이틀 및 버튼 한 줄 배치
st.set_page_config(page_title="어린이 맞춤형 수학 학습지", layout="wide")
col_title, col1, col2, col3, col4 = st.columns([8, 1, 1, 1, 1])
with col_title:
    st.markdown("### 🧠 어린이 맞춤형 수학 학습지")
with col1:
    if not st.session_state.logged_in:
        st.markdown('<div style="background-color:#ffe4e1; padding:4px; border-radius:8px;">', unsafe_allow_html=True)
        if st.button("🔑 Login", key="top_login_btn"):
            st.session_state.show_login = True
            st.session_state.show_register = False
        st.markdown('</div>', unsafe_allow_html=True)
with col2:
    if not st.session_state.logged_in:
        st.markdown('<div style="background-color:#e0ffe1; padding:4px; border-radius:8px;">', unsafe_allow_html=True)
        if st.button("🧒 Regist", key="top_register_btn"):
            st.session_state.show_register = True
            st.session_state.show_login = False
        st.markdown('</div>', unsafe_allow_html=True)
with col3:
    if st.session_state.logged_in:
        st.markdown('<div style="background-color:#e1e7ff; padding:4px; border-radius:8px;">', unsafe_allow_html=True)
        if st.button("🚪 Logout", key="top_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.child_id = None
            st.session_state.child_name = None
            st.session_state.child_pw = None
            st.session_state.child_grade = None
            st.session_state.child_semester = None
            st.session_state.selected_lesson = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# 아동 프로필 생성 입력 폼 (모달 대체)
if st.session_state.show_register:
    st.markdown("### 아동 프로필 생성")
    reg_id = st.text_input("ID", key="reg_id")
    reg_name = st.text_input("이름", key="reg_name")
    reg_pw = st.text_input("PW", type="password", key="reg_pw")
    reg_grade = st.number_input("학년", min_value=1, max_value=6, step=1, key="reg_grade")
    reg_semester = st.number_input("학기", min_value=1, max_value=2, step=1, key="reg_semester")
    if st.button("등록", key="register_btn"):
        if reg_id and reg_name and reg_pw and reg_grade and reg_semester:
            if get_account(reg_id):
                st.warning("이미 존재하는 ID입니다. 다른 ID를 입력하세요.")
            else:
                add_account(reg_id, reg_name, reg_pw, reg_grade, reg_semester)
                st.session_state.child_id = reg_id
                st.session_state.child_name = reg_name
                st.session_state.child_pw = reg_pw
                st.session_state.child_grade = reg_grade
                st.session_state.child_semester = reg_semester
                st.session_state.logged_in = True
                st.session_state.show_register = False
                st.session_state.overall_feedback_text = None
                st.session_state.overall_feedback_needed = True
                st.rerun()
        else:
            st.warning("모든 정보를 입력하세요.")
    if st.button("닫기", key="close_register"):
        st.session_state.show_register = False
    st.stop()

# 로그인 입력 폼 (모달 대체)
if st.session_state.show_login:
    st.markdown("### 로그인")
    login_id = st.text_input("ID", key="login_id")
    login_pw = st.text_input("PW", type="password", key="login_pw")
    if st.button("로그인", key="login_btn"):
        if login_id and login_pw:
            acc = get_account(login_id)
            if acc and acc["pw"] == login_pw:
                st.session_state.child_id = login_id
                st.session_state.child_name = acc["name"]
                st.session_state.child_pw = login_pw
                st.session_state.child_grade = acc["grade"]
                st.session_state.child_semester = acc["semester"]
                st.session_state.logged_in = True
                st.session_state.show_login = False
                # 종합 피드백은 첫 진입 시 생성하도록 플래그 설정
                st.session_state.overall_feedback_text = None
                st.session_state.overall_feedback_needed = True
                st.rerun()
            else:
                st.warning("ID 또는 PW가 일치하지 않습니다.")
        else:
            st.warning("ID, PW를 입력하세요.")
    if st.button("닫기", key="close_login"):
        st.session_state.show_login = False
    st.stop()

# 로그인 전 메인
if not st.session_state.logged_in:
    st.markdown("""
    # 어린이 맞춤형 AI 수학 학습 서비스
    AI가 아이의 학년과 학기에 맞는 수학 문제를 만들어주고, 풀이 과정을 도와줍니다.\n
    1. 우측 상단에서 아동 프로필을 생성하거나 로그인하세요.\n
    2. 로그인 후 학습 이력 확인, 새 학습지 생성, 문제 풀이 및 피드백을 경험할 수 있습니다.
    """)
else:
    acc = get_account(st.session_state.child_id)
    setup_ui_styles()
    with st.sidebar:
        # 🎓 학생 정보 카드
        st.markdown(f"""
        <div class='sidebar-student-card'>
            <div class='student-name'>{acc['name']}</div>
            <div class='student-grade'>{acc['grade']}학년 {acc['semester']}학기</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 📚 학습지 생성 옵션 섹션
        st.markdown("""
        <div class='sidebar-section'>
            <div class='sidebar-section-title'>📚 학습지 생성</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 학년 선택
        selected_grade = st.selectbox(
            "학년 선택",
            options=[1, 2, 3, 4, 5, 6],
            index=[1, 2, 3, 4, 5, 6].index(int(acc['grade'])),
            key="grade_select"
        )
        
        # 학기 선택
        selected_semester = st.selectbox(
            "학기 선택",
            options=[1, 2],
            index=[1, 2].index(int(acc['semester'])),
            key="semester_select"
        )
        
        # 커리큘럼 선택을 위한 subjects 로드
        curriculum_subjects = load_curriculum_subjects(selected_grade, selected_semester)
        
        if curriculum_subjects:
            selected_subject = st.selectbox(
                "단원 선택",
                options=["전체 (랜덤)"] + curriculum_subjects,
                index=0,
                key="subject_select"
            )
        else:
            selected_subject = "전체 (랜덤)"
            st.warning(f"{selected_grade}학년 {selected_semester}학기 커리큘럼을 찾을 수 없습니다.")
        
        # 추가 요청 입력 (100자 제한)
        # 두 줄 기본 높이를 위해 text_area 사용. 100자 제한은 코드로 보장
        extra_request_raw = st.text_area(
            "추가 요청 (선택, 100자 이내)",
            key="extra_request_input",
            height=72,
        )
        extra_request = (extra_request_raw or "").strip()
        if len(extra_request) > 100:
            st.caption(f"입력 {len(extra_request)}자 중 처음 100자만 전송됩니다.")
            extra_request = extra_request[:100]

        if st.button("🎯 새 학습지 생성", key="create_lesson_btn", type="primary"):
            payload = {
                "child_id": acc["id"],
                "name": acc["name"],
                "grade": selected_grade,
                "semester": selected_semester,
                "subject": selected_subject if selected_subject != "전체 (랜덤)" else None,
                "extra_request": (extra_request or None)
            }
            with st.spinner("AI가 학습지를 만들고 있어요..."):
                resp = requests.post(urljoin(API_URL, "/init_profile"), json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    # 선택된 단원 정보로 제목 생성
                    subject_text = f" - {selected_subject}" if selected_subject != "전체 (랜덤)" else ""
                    extracted_title = (data.get('lesson') or '').split(']')[-1].split('\n')[0].strip() if isinstance(data.get('lesson'), str) else '수학'

                    lesson_item = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "title": f"{selected_grade}학년 {selected_semester}학기 {extracted_title}{subject_text}",
                        "lesson_id": data["lesson_id"],
                        "content": data["lesson"],
                        "materials_text": data["materials_text"],
                        "feedback": None
                    }
                    add_history(acc["id"], lesson_item["lesson_id"], lesson_item["date"], lesson_item["title"], lesson_item["content"], lesson_item["materials_text"])
                    st.session_state.selected_lesson = lesson_item
                    st.session_state.feedback = None
                    # 학습 세션 중에는 종합 피드백 자동 호출 방지
                    st.session_state.overall_feedback_needed = False
                    st.success("✅ 학습지가 생성되었습니다! 메인 화면에서 확인하세요.")
                    st.rerun()
                else:
                    st.error(f"오류 발생: {resp.text}")
        # 📊 학습 이력 섹션
        st.markdown("""
        <div class='sidebar-section'>
            <div class='sidebar-section-title'>📊 학습 이력</div>
        </div>
        """, unsafe_allow_html=True)
        
        history = get_history(acc["id"])
        if history:
            for idx, item in enumerate(history):
                # 점수 파싱
                score_text = ""
                if item.get('feedback'):
                    import re as _re
                    m = _re.search(r"총점:\s*(\d+)\s*점", item['feedback'])
                    if m:
                        score_text = f"{m.group(1)}점"
                unit_title = item['title']

                # 버튼 내부에 점수 포함, 한 줄 표시 유지
                truncated_title = unit_title[:28] + ("..." if len(unit_title) > 28 else "")
                score_inline = f"  · {score_text}" if score_text else "  · 점수 없음"

                # 클릭 가능한 이력 카드 (박스)
                if st.button(
                    label=f"📝 {truncated_title}{score_inline}",
                    key=f"lesson_{idx}",
                    help=f"{unit_title}\n{item['date']}"
                ):
                    st.session_state.selected_lesson = item
                    st.rerun()

    # 메인: 학습 상세/진행
    if st.session_state.selected_lesson:
        lesson = st.session_state.selected_lesson
        st.markdown(f"### {lesson['title']}")
        # 상단 원문(정답/해설 포함 가능성) 노출 방지: 제목/헤더만 표기
        header_line = (lesson['content'] or '').split('\n', 1)[0]
        if header_line:
            st.markdown(f"<div class='worksheet-title'>{header_line}</div>", unsafe_allow_html=True)
        st.markdown("---")
        # 파싱하여 예쁘게 문제 카드 + 바로 아래 답안 입력 렌더링
        parsed = parse_worksheet(lesson['materials_text'])
        answer_keys = [f"answer_{i+1}" for i in range(len(parsed))]
        # 난이도 뱃지 색상(파스텔)
        badge_colors = {
            'basic': '#e0f2fe',
            'reason': '#fef9c3',
            'applied_basic': '#d1fae5',
            'applied_adv': '#fde68a',
        }
        # 각 문제에 배지 매핑(1-3 기본, 4-5 추론, 6-8 응용기본, 9-10 응용중고급)
        def get_badge(i):
            if i < 3:
                return ('기본', badge_colors['basic'])
            if i < 5:
                return ('추론', badge_colors['reason'])
            if i < 8:
                return ('응용', badge_colors['applied_basic'])
            return ('중고급', badge_colors['applied_adv'])

        for i, item in enumerate(parsed):
            label, color = get_badge(i)
            # 타입 표기 제거 요청: 문제타입 텍스트는 카드 안에 넣지 않음. 대신 작은 배지로만 색상만 표시(텍스트 미표시)
            st.markdown(
                f"<div class='problem-card'>"
                f"<div style='display:flex; gap:8px; align-items:center; margin-bottom:6px;'>"
                f"  <div class='problem-header'>문제 {item['number']}</div>"
                f"  <div style='width:14px; height:14px; border-radius:7px; background:{color}; border:1px solid rgba(0,0,0,0.06);'></div>"
                f"</div>"
                f"<div class='problem-text'>{item['text']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            # 라디오 버튼 보기 UI
            options = [f"A) {item['choices'].get('A','')}", f"B) {item['choices'].get('B','')}", f"C) {item['choices'].get('C','')}", f"D) {item['choices'].get('D','')}"]
            default_idx = 0
            sel = st.radio(
                " ",
                options,
                key=answer_keys[i],
                horizontal=True,
                index=None,
                label_visibility="collapsed",
            )
        
        if lesson.get('feedback'):
            st.markdown("---")
            st.markdown("#### 채점 결과")
            st.write(lesson['feedback'])
        else:
            st.markdown("---")
            st.markdown("#### 정답 입력")
            # 입력값 수집 + 검증(A/B/C/D만 허용) 및 미입력 경고
            parsed = parse_worksheet(lesson['materials_text'])
            num_questions = len(parsed)
            answer_inputs = []
            invalid = False
            missing = False
            for i in range(num_questions):
                sel = st.session_state.get(f"answer_{i+1}")
                if not sel:
                    missing = True
                    answer_inputs.append(f"{i+1}번 답: ")
                    continue
                # 라디오 값에서 옵션 문자 추출 (예: 'B) 보기')
                label = sel.split(')')[0].strip() if ')' in sel else sel.strip()
                if label not in ['A', 'B', 'C', 'D']:
                    invalid = True
                answer_inputs.append(f"{i+1}번 답: {label}")

            if st.button("정답 제출", key="submit_assessment_btn"):
                if missing:
                    st.warning("모든 문항의 정답을 선택해주세요.")
                elif invalid:
                    st.warning("정답은 A/B/C/D 중 하나여야 합니다.")
                else:
                    responses_text = "\n".join(answer_inputs)
                    payload = {
                        "child_id": acc["id"],
                        "lesson_id": lesson["lesson_id"],
                        "responses_text": responses_text,
                        "materials_text": lesson["materials_text"]
                    }
                    with st.spinner("AI가 채점하고 있어요..."):
                        try:
                            resp = requests.post(urljoin(API_URL, "/submit_assessment"), json=payload)
                            if resp.status_code == 200:
                                data = resp.json()
                                # 서버에서 받은 피드백 표시 (점수/해설/피드백 포함)
                                st.session_state.feedback = data.get("feedback", "")
                                update_feedback(acc["id"], lesson["lesson_id"], st.session_state.feedback)
                                st.markdown("---")
                                st.markdown("#### 평가 결과")
                                # 결과를 카드 스타일로 재가공 렌더링 시도
                                fb_md = st.session_state.feedback or ""
                                # 간단 파싱: 섹션별 분리
                                score_part = fb_md
                                perq_part = ""
                                expl_part = ""
                                feed_part = ""
                                if "[PerQuestion]" in fb_md:
                                    score_part, rest = fb_md.split("[PerQuestion]", 1)
                                    if "[Explanations]" in rest:
                                        perq_part, rest2 = rest.split("[Explanations]", 1)
                                        if "[Feedback]" in rest2:
                                            expl_part, feed_part = rest2.split("[Feedback]", 1)
                                        else:
                                            expl_part = rest2
                                    else:
                                        perq_part = rest
                                st.markdown(f"<div class='problem-card'><div class='problem-header'>총점</div><div class='problem-text'>{score_part}</div></div>", unsafe_allow_html=True)
                                def _nl2br(s: str) -> str:
                                    return (s or '').replace('\n', '<br/>')
                                if perq_part.strip():
                                    table_html = render_per_question_table(perq_part)
                                    if table_html:
                                        st.markdown(f"<div class='problem-card'><div class='problem-header'>문항별 결과</div><div class='problem-text'>{table_html}</div></div>", unsafe_allow_html=True)
                                    else:
                                        html = _nl2br(perq_part)
                                        st.markdown(f"<div class='problem-card'><div class='problem-header'>문항별 결과</div><div class='problem-text'>{html}</div></div>", unsafe_allow_html=True)
                                if expl_part.strip():
                                    html = _nl2br(expl_part)
                                    st.markdown(f"<div class='problem-card'><div class='problem-header'>해설</div><div class='problem-text'>{html}</div></div>", unsafe_allow_html=True)
                                if feed_part.strip():
                                    html = _nl2br(feed_part)
                                    st.markdown(f"<div class='problem-card'><div class='problem-header'>종합 피드백</div><div class='problem-text'>{html}</div></div>", unsafe_allow_html=True)
                            else:
                                st.error(f"오류 발생: {resp.text}")
                        except Exception as e:
                            st.error(f"요청 중 오류 발생: {e}")

    else:
        history = get_history(st.session_state.child_id)
        if history:
            st.markdown("## 📊 AI 종합 피드백")
            # 최초 로그인 시 1회 호출하여 저장, 이후에는 캐시된 텍스트만 사용
            if (not st.session_state.overall_feedback_text) and (st.session_state.get("overall_feedback_needed", True)):
                with st.spinner("AI가 종합 피드백을 만들고 있어요..."):
                    history_for_feedback = get_history_for_feedback(history)
                    payload = {
                        "name": acc["name"],
                        "grade": acc["grade"],
                        "semester": acc["semester"],
                        "history": history_for_feedback
                    }
                    resp = requests.post(urljoin(API_URL, "/overall_feedback"), json=payload)
                    if resp.status_code == 200:
                        st.session_state.overall_feedback_text = resp.json().get("feedback", "")
                        st.session_state.overall_feedback_needed = False
                    else:
                        st.session_state.overall_feedback_text = "종합 피드백 생성에 실패했습니다."
                        st.session_state.overall_feedback_needed = False
            # 비어있지 않은 문자열인지 확인 후 렌더
            ofb = st.session_state.overall_feedback_text
            if isinstance(ofb, str) and ofb.strip():
                st.markdown(ofb, unsafe_allow_html=True)
            else:
                st.info("종합 피드백을 불러오는 중 문제가 있었습니다. 좌측에서 학습을 시작하면 더 정확한 리포트를 만들 수 있어요.")
        else:
            st.markdown("""
            # 👋 처음 오셨군요!
            좌측 사이드바에서 **새 학습지 생성** 버튼을 눌러 첫 학습을 시작해보세요.
            """)
