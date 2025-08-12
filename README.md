# 🧮 childMathStudyAI

AI 기반 초등학생 맞춤형 수학 학습지 생성 시스템

## 🌟 주요 기능

- **RAG 기반 문제 생성**: PDF 교육과정 가이드와 JSON 교육과정을 ChromaDB에 임베딩하여 고품질 수학 문제 생성
- **학년/학기별 맞춤 학습**: 1-6학년, 1-2학기별 교육과정에 정확히 맞는 문제 출제
- **아동 친화적 UI**: Jua 폰트, 파스텔 테마, 카드 기반 디자인으로 어린이가 사용하기 쉬운 인터페이스
- **실시간 피드백**: 정답 제출 즉시 점수, 해설, 개별 문제별 정오 표시
- **학습 이력 관리**: 개인별 학습 진도와 성취도 추적

## 🏗️ 시스템 아키텍처

```
Frontend (Streamlit) → Backend (FastAPI) → LangGraph Workflow → Azure OpenAI + ChromaDB
```

### 주요 구성 요소

- **Frontend**: Streamlit 기반 웹 인터페이스
- **Backend**: FastAPI 기반 REST API
- **Workflow**: LangGraph를 활용한 학습 워크플로우
- **RAG System**: ChromaDB + Azure OpenAI를 활용한 검색 증강 생성
- **Database**: SQLite (사용자 정보, 학습 이력)

## 🚀 설치 및 실행

### 1. 환경 요구사항

- Python 3.10+
- Azure OpenAI Service 계정
- Git

### 2. 저장소 클론

```bash
git clone https://github.com/zowhba/childMathStudyAI.git
cd childMathStudyAI
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 설정하세요:

```env
# Azure OpenAI Configuration
AOAI_ENDPOINT=https://your-azure-openai-resource.openai.azure.com/
AOAI_API_KEY=your_azure_openai_api_key_here
AOAI_DEPLOY_GPT4O=your_gpt4o_deployment_name
AOAI_DEPLOY_EMBED_3_LARGE=your_text_embedding_3_large_deployment_name

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db
```

**⚠️ 중요**: 기존 `AZURE_OPENAI_*` 환경변수는 더 이상 사용하지 않습니다. 반드시 새로운 `AOAI_*` 변수명을 사용하세요.

### 5. 서버 실행

#### Backend (FastAPI)
```bash
uvicorn main:app --reload
```

#### Frontend (Streamlit)
```bash
streamlit run streamlit_app.py
```

## 📖 사용법

### 1. 회원 가입/로그인
- 이름, 학년, 학기 정보 입력

### 2. 학습지 생성
- "새 학습지 생성" 버튼 클릭
- AI가 해당 학년/학기에 맞는 10문제 생성 (기본 3문제, 추론 2문제, 응용 3문제, 고급응용 2문제)

### 3. 문제 풀이
- 4지선다 문제를 라디오 버튼으로 선택
- 모든 문제 답변 후 "정답 제출" 클릭

### 4. 결과 확인
- 100점 만점 점수 확인
- 문제별 정답/오답 여부 (O/X) 확인
- 상세한 해설과 피드백 제공

### 5. 학습 이력
- 개인별 학습 진도와 점수 이력 확인

## 🎨 UI/UX 특징

- **Jua 폰트**: 어린이가 읽기 쉬운 한글 폰트
- **파스텔 테마**: 밝고 부드러운 색상 조합
- **카드 기반 디자인**: 문제별로 구분된 카드 레이아웃
- **즉시 피드백**: 답안 제출 후 실시간 결과 표시
- **반응형 디자인**: 다양한 화면 크기 지원

## 🤖 RAG 시스템

### 문서 임베딩
- **PDF 가이드**: `resource/Math_curriculum_guid.pdf`
- **교육과정 JSON**: `resource/curriculum.json`

### 검색 및 생성
1. 학년/학기별 교육과정 단원 검색
2. 관련 교육 가이드 문서 유사도 검색
3. 검색 결과를 바탕으로 고품질 수학 문제 생성

### 비용 최적화
- ChromaDB 데이터 존재 여부 확인
- 필요한 경우에만 임베딩 수행
- 중복 임베딩 방지로 Azure OpenAI 비용 절약

## 📁 프로젝트 구조

```
childMathStudyAI/
├── app/
│   ├── models/schemas.py          # 데이터 모델
│   ├── services/
│   │   ├── azure_openai_service.py    # Azure OpenAI 연동
│   │   ├── vector_db_service.py       # ChromaDB 관리
│   │   └── rag_service.py             # RAG 시스템
│   └── workflow/
│       ├── graph.py               # LangGraph 워크플로우 정의
│       └── nodes.py               # 워크플로우 노드 구현
├── prompts/                       # AI 프롬프트 템플릿
├── resource/                      # 교육과정 리소스
├── main.py                        # FastAPI 백엔드
├── streamlit_app.py              # Streamlit 프론트엔드
└── requirements.txt              # Python 의존성
```

## 🔧 개발 정보

### 기술 스택
- **Backend**: FastAPI, LangGraph, ChromaDB
- **Frontend**: Streamlit
- **AI**: Azure OpenAI (GPT-4o, Text Embedding 3 Large)
- **Database**: SQLite, ChromaDB
- **Language**: Python 3.10+

### 주요 라이브러리
- `fastapi`: REST API 서버
- `streamlit`: 웹 인터페이스
- `langgraph`: AI 워크플로우 오케스트레이션
- `chromadb`: 벡터 데이터베이스
- `openai`: Azure OpenAI 연동
- `PyPDF2`: PDF 문서 파싱

## 📝 라이선스

MIT License

## 👨‍💻 개발자

**zowhba** - [GitHub](https://github.com/zowhba)

---

📧 문의사항이나 버그 리포트는 [Issues](https://github.com/zowhba/childMathStudyAI/issues)에 등록해주세요.

## 🧭 프로그램 가이드

### 전체 흐름 개요
- **초기 프로필 입력 → 교육과정/가이드 검색(RAG) → 학습지 생성 → 문제 풀이/제출 → 결정론 채점 → 해설/피드백 생성 → 종합 리포트**
- 워크플로우 정의: `app/workflow/graph.py`
  - `create_init_profile_graph()`: 프로필 확인 → 교육과정 조회 → 학습지 생성
  - `create_assessment_graph()`: 평가 응답 저장 → 피드백 생성(채점 포함)
  - `create_overall_feedback_graph()`: 학습 이력 기반 종합 피드백 생성

### 핵심 노드와 역할 (`app/workflow/nodes.py`)
- `init_profile_node`: 입력 프로필 확인
- `fetch_course_node`: `RAGService.get_curriculum_units()`로 단원 목록 조회 + `VectorDBService.query_by_grade_semester()`로 관련 문서 조회
- `generate_materials_node`: `AzureOpenAIService.generate_materials_for_grade_semester_with_rag()`로 단원 기반 10문항 학습지 생성, `lesson_id` 발급
- `submit_assessment_node`: 응답/문항 텍스트를 ChromaDB에 저장
- `create_feedback_node`: 결정론 채점 + 해설·간단 피드백 생성
- `create_overall_feedback_node`: 템플릿 기반 종합 리포트 생성

### 프롬프트 템플릿 (`prompts/`)
- `materials.txt`: 10문항 학습지 생성 지침 및 출력 포맷
- `feedback.txt`: 제출 답안에 대한 채점/해설/피드백 출력 포맷
- `next_material.txt`: 이전 학습 반영 다음 교재 안내(옵션)
- `initial_curriculum.txt`: 초기 커리큘럼 주제 제안
- `feedback_summary.txt`: 학습 이력 기반 종합 리포트(요약/추천/응원)

### RAG 초기화와 검색 (`app/services/rag_service.py`)
- 앱 시작 시 `startup` 훅에서 자동 초기화: `initialize_rag_data()`
  - PDF 가이드: `resource/Math_curriculum_guid.pdf` → 컬렉션 `math_curriculum_guide`
  - 교육과정 JSON: `resource/curriculum.json` → 컬렉션 `curriculum_units`
- 이미 데이터가 있으면 재임베딩을 건너뛰어 **비용 절감**
- 단원별 가이드 검색: `search_unit_guide(unit_name, grade, semester, top_k)`

### 결정론 객관식 채점 규칙 (`app/services/azure_openai_service.py`)
- 함수: `grade_multiple_choice(materials_text, responses_text)`
  - `[Worksheet]`와 `[AnswerKey]`를 파싱해 정답 맵 생성
  - 학생 응답을 라인 규칙으로 파싱: `1번 답: A` 형태
  - 총점은 정답 일치 개수 기반으로 계산(정수 점수)
  - 결과 섹션 출력
    - `[Score]`: 총점
    - `[PerQuestion]`: `n) 학생:(X) | 정답:(Y) | 채점: O/X`
    - `[Explanations]`: LLM이 생성한 해설에 정답 표기 강제 결합
    - `[Feedback]`: 간단 규칙 기반 코멘트

### API 엔드포인트 (`main.py`)
- `POST /init_profile` → `LearningResponse`
  - 입력: `ChildProfileInput { child_id, name, grade, semester, subject?, extra_request? }`
  - 동작: 프로필 → 단원/RAG 조회 → 학습지 생성 + `lesson_id` 반환
- `POST /submit_assessment` → `FeedbackResponse`
  - 입력: `AssessmentInput { child_id, lesson_id, responses_text, materials_text }`
  - 동작: 응답 저장 → 결정론 채점 → 해설/피드백 포함 결과
- `POST /overall_feedback` → `{ feedback: string }`
  - 입력: `{ name, grade, semester, history: [{topic, feedback}] }`
  - 동작: 이력 요약, 방향 제안, 응원 메시지 포함 리포트 생성

### 환경 변수(.env)
```env
# Azure OpenAI
AOAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AOAI_API_KEY=YOUR_KEY
AOAI_DEPLOY_GPT4O=your_gpt4o_deployment
AOAI_DEPLOY_EMBED_3_LARGE=your_text_embedding_3_large

# ChromaDB
CHROMA_DB_PATH=./chroma_db

# Frontend → Backend 연결(옵션)
API_URL=http://localhost:8000
```
– 기존 `AZURE_OPENAI_*` 명은 사용하지 않으며, 반드시 `AOAI_*`를 사용합니다.

### 실행 시나리오
1) 백엔드 기동
```bash
uvicorn main:app --reload
```
2) 프론트엔드 기동
```bash
streamlit run streamlit_app.py
```
3) 사용 흐름
- 회원가입/로그인 → 좌측 사이드바에서 학년/학기/단원(옵션) 선택 → "새 학습지 생성"
- 메인 영역에서 문제 풀이 → "정답 제출" → 점수/문항별 결과/해설/요약 피드백 확인
- 상단 "AI 종합 피드백" 섹션에서 이력 기반 리포트 확인

### 도커 사용(옵션)
```bash
docker-compose up --build -d
```
- 서비스: `api`(FastAPI), `chroma`(ChromaDB)
- 볼륨: `chroma_data`에 영구 저장

### 유틸리티(옵션)
- `view_chromadb_app.py`: ChromaDB 컬렉션/문서 뷰어(UI)
- `streamlit_db_manager.py`: SQLite(`child_edu_ai.db`) 테이블 스키마/데이터 조회
