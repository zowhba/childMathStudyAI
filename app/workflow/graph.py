from langgraph.graph import StateGraph, START, END
from app.workflow.nodes import (
    init_profile_node,
    fetch_course_node,
    generate_materials_node,
    submit_assessment_node,
    create_feedback_node,
    create_overall_feedback_node
)
from app.models.schemas import EducationWorkflowState

def create_init_profile_graph() -> StateGraph:
    """초기 프로필 기반 교재 생성 워크플로우"""
    graph = StateGraph(state_schema=EducationWorkflowState)
    
    # 노드 추가
    graph.add_node("init_profile", init_profile_node)
    graph.add_node("fetch_course", fetch_course_node)
    graph.add_node("generate_materials", generate_materials_node)
    
    # 엣지 연결
    graph.add_edge(START, "init_profile")
    graph.add_edge("init_profile", "fetch_course")
    graph.add_edge("fetch_course", "generate_materials")
    graph.add_edge("generate_materials", END)
    
    return graph.compile()

def create_assessment_graph() -> StateGraph:
    """평가 제출 및 피드백 생성 워크플로우"""
    graph = StateGraph(state_schema=EducationWorkflowState)
    
    # 노드 추가
    graph.add_node("submit_assessment", submit_assessment_node)
    graph.add_node("create_feedback", create_feedback_node)
    
    # 엣지 연결
    graph.add_edge(START, "submit_assessment")
    graph.add_edge("submit_assessment", "create_feedback")
    graph.add_edge("create_feedback", END)
    
    return graph.compile()

def create_overall_feedback_graph() -> StateGraph:
    """학습 이력 기반 종합 피드백 워크플로우"""
    graph = StateGraph(state_schema=EducationWorkflowState)
    graph.add_node("create_overall_feedback", create_overall_feedback_node)
    graph.add_edge(START, "create_overall_feedback")
    graph.add_edge("create_overall_feedback", END)
    return graph.compile()
