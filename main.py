from fastapi import FastAPI, Body
from app.models.schemas import ChildProfileInput, LearningResponse, AssessmentInput, FeedbackResponse, EducationWorkflowState, FeedbackHistoryItem, OverallFeedbackRequest
from app.workflow.graph import create_init_profile_graph, create_assessment_graph, create_overall_feedback_graph
from app.services.rag_service import RAGService
from app.services.vector_db_service import VectorDBService
from app.services.azure_openai_service import AzureOpenAIService
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from typing import List

# 환경변수 로드
load_dotenv()

app = FastAPI(title="어린이 맞춤형 교재 생성기 API")

# 서비스 초기화
vector_service = VectorDBService(persist_directory=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
azure_service = AzureOpenAIService(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    key=os.getenv("AZURE_OPENAI_API_KEY"),
    dep_curriculum=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM"),
    dep_embed=os.getenv("AZURE_OPENAI_DEPLOY_EMBED")
)
rag_service = RAGService(vector_service, azure_service)

# LangGraph 워크플로우 초기화
init_profile_workflow = create_init_profile_graph()
assessment_workflow = create_assessment_graph()
overall_feedback_workflow = create_overall_feedback_graph()

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작시 RAG 데이터 초기화"""
    print("RAG 시스템 초기화 중...")
    success = rag_service.initialize_rag_data()
    if success:
        print("RAG 시스템 초기화 완료")
    else:
        print("RAG 시스템 초기화 실패")

@app.post("/init_profile", response_model=LearningResponse)
async def init_profile(profile: ChildProfileInput):
    """
    1) 아동 프로필 입력 받음
    2) 초기 학습 커리큘럼 생성
    3) 교재 및 문제 생성 후 반환
    """
    # LangGraph 워크플로우 실행
    initial_state = EducationWorkflowState(child_profile=profile)
    final_state = init_profile_workflow.invoke(initial_state)
    
    if final_state.get("learning_response"):
        return final_state["learning_response"]
    else:
        raise Exception("교재 생성에 실패했습니다.")

@app.post("/submit_assessment", response_model=FeedbackResponse)
async def submit_assessment(assessment: AssessmentInput):
    """
    1) 평가 응답 저장
    2) 피드백 생성
    3) 다음 교재 생성
    """
    # LangGraph 워크플로우 실행
    initial_state = EducationWorkflowState(assessment_input=assessment)
    final_state = assessment_workflow.invoke(initial_state)
    
    if final_state.get("feedback_response"):
        return final_state["feedback_response"]
    else:
        raise Exception("피드백 생성에 실패했습니다.")

@app.post("/overall_feedback")
async def overall_feedback(req: OverallFeedbackRequest):
    # print("[DEBUG] /overall_feedback request body:", req)
    # 워크플로우 상태 준비
    state = EducationWorkflowState()
    # child_profile은 최소한 이름, 나이 필요
    state.child_profile = ChildProfileInput(
        child_id="dummy",  # 필요시 req에 추가
        name=req.name,
        grade=req.grade,
        semester=req.semester
    )
    state.history = [item.dict() for item in req.history]
    # print("[DEBUG] state.history:", state.history)
    final_state = overall_feedback_workflow.invoke(state)
    if final_state.get("overall_feedback_response"):
        return {"feedback": final_state["overall_feedback_response"].feedback}
    else:
        raise Exception("종합 피드백 생성에 실패했습니다.")
