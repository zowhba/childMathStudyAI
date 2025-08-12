import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

import uuid
from app.services.azure_openai_service import AzureOpenAIService
from app.services.vector_db_service import VectorDBService
from app.services.rag_service import RAGService
from app.models.schemas import EducationWorkflowState, LearningResponse, FeedbackResponse, OverallFeedbackResponse

key = os.getenv("AZURE_OPENAI_API_KEY")
if not key:
    raise RuntimeError("환경변수 AZURE_OPENAI_API_KEY가 설정되어 있지 않습니다.")
azure_service = AzureOpenAIService(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    key=key,
    dep_curriculum=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM"),
    dep_embed=os.getenv("AZURE_OPENAI_DEPLOY_EMBED"),
)
vector_service = VectorDBService(persist_directory=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
rag_service = RAGService(vector_service, azure_service)

def init_profile_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """아동 프로필 정보 확인 (현재는 특별한 동작 없음)"""
    return state

def fetch_course_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """학년/학기 기반 교육과정 조회 (RAG 시스템 사용)"""
    if state.child_profile:
        # RAG 시스템에서 해당 학년/학기의 교육과정 단원 조회
        units = rag_service.get_curriculum_units(
            grade=state.child_profile.grade,
            semester=state.child_profile.semester
        )
        
        # 기존 ChromaDB 검색도 병행 (호환성 유지)
        docs = vector_service.query_by_grade_semester(
            grade=state.child_profile.grade,
            semester=state.child_profile.semester
        )
        
        state.related_docs = docs
        state.curriculum_units = units  # 새로운 필드 추가
    return state

def generate_materials_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """맞춤 교재 및 평가 문제 생성 (자료가 없어도 생성되도록)"""
    if state.child_profile:
        curriculum_text = f"{state.child_profile.grade}학년 {state.child_profile.semester}학기 수학"
        related_docs = state.related_docs or []
        # RAG 시스템에서 교육과정 가이드 검색
        curriculum_units = getattr(state, 'curriculum_units', [])
        curriculum_guide = ""
        if curriculum_units:
            # 첫 번째 단원에 대한 가이드 검색
            unit_name = curriculum_units[0] if curriculum_units else ""
            guide_results = rag_service.search_unit_guide(
                unit_name=unit_name,
                grade=state.child_profile.grade,
                semester=state.child_profile.semester,
                top_k=3
            )
            
            if guide_results:
                curriculum_guide = "\n\n".join([result["content"] for result in guide_results[:2]])
        
        # 학년/학기에 맞는 주제를 자동 선택하여 문제 생성 (RAG 가이드 포함)
        lesson, materials = azure_service.generate_materials_for_grade_semester_with_rag(
            state.child_profile.grade,
            state.child_profile.semester,
            related_docs,
            curriculum_units,
            curriculum_guide
        )
        lesson_id = azure_service.save_lesson(state.child_profile.child_id, lesson, related_docs)

        state.lesson = lesson
        state.materials = materials
        state.lesson_id = lesson_id

        materials_text = "\n".join(materials)
        state.learning_response = LearningResponse(
            lesson=lesson,
            materials_text=materials_text,
            lesson_id=lesson_id
        )
    return state

def submit_assessment_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """평가 응답 저장"""
    if state.assessment_input:
        vector_service.add_assessment(
            student_id=state.assessment_input.child_id,
            lesson_id=state.assessment_input.lesson_id,
            responses=[state.assessment_input.responses_text],
            materials_text=state.assessment_input.materials_text,
            azure_service=azure_service
        )
        state.responses = state.assessment_input.responses_text
    return state

def create_feedback_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """피드백 및 다음 교재 생성"""
    if state.responses and state.assessment_input:
        # 결정론적 객관식 채점으로 정확도 향상
        feedback = azure_service.grade_multiple_choice(
            state.assessment_input.materials_text,
            state.responses
        )
        state.feedback = feedback
        state.feedback_response = FeedbackResponse(
            feedback=feedback
        )
    return state

def create_overall_feedback_node(state: EducationWorkflowState) -> EducationWorkflowState:
    """학습 이력 기반 종합 피드백 생성"""
    # 필요한 정보: 이름, 나이, 이력 리스트(history)
    if state.child_profile and hasattr(state, 'history') and state.history:
        # history: [{interests, topic, feedback}, ...] 형태로 가정
        feedback = azure_service.create_overall_feedback(
            name=state.child_profile.name,
            grade=state.child_profile.grade,
            semester=state.child_profile.semester,
            history=state.history
        )
        state.overall_feedback_response = OverallFeedbackResponse(feedback=feedback)
    return state
