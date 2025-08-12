from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

import json
from typing import Optional


from dotenv import load_dotenv
load_dotenv()

#실습용 AOAI 환경변수 읽기
import os
# Jinja2 템플릿 로더 설정
# env = Environment(loader=FileSystemLoader(template_dir))
# AOAI_ENDPOINT=os.getenv("AOAI_ENDPOINT")
# AOAI_API_KEY=os.getenv("AOAI_API_KEY")
# AOAI_DEPLOY_GPT4O=os.getenv("AOAI_DEPLOY_GPT4O")
# AOAI_DEPLOY_GPT4O_MINI=os.getenv("AOAI_DEPLOY_GPT4O_MINI")
# AOAI_DEPLOY_EMBED_3_LARGE=os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")
# AOAI_DEPLOY_EMBED_3_SMALL=os.getenv("AOAI_DEPLOY_EMBED_3_SMALL")
# AOAI_DEPLOY_EMBED_ADA=os.getenv("AOAI_DEPLOY_EMBED_ADA")


AOAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")
AOAI_API_KEY=os.getenv("AZURE_OPENAI_API_KEY")
AOAI_DEPLOY_GPT4O=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM")
AOAI_DEPLOY_GPT4O_MINI=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM")
AOAI_DEPLOY_EMBED_3_LARGE=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM")
AOAI_DEPLOY_EMBED_3_SMALL=os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM")
AOAI_DEPLOY_EMBED_ADA=os.getenv("AZURE_OPENAI_DEPLOY_EMBED")

llm = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    azure_deployment=AOAI_DEPLOY_GPT4O,
    api_version="2024-10-21",
    api_key=AOAI_API_KEY
)

members = ["loan_manager", "tax_accountant"]
# Our team supervisor is an LLM node. It just picks the next agent to process
# and decides when the work is completed
options = members + ["FINISH"]

system_prompt = (
    "You are a real_estate_agent tasked with managing a conversation between the"
    " following workers: {members}. Given the following user request,"
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with FINISH."
)

@tool
def get_loan_product(day: Optional[str] = None):
    """
    대출 상품을 조회하는 tool
    
    :return: 로컬 변수에 정의된 JSON 데이터를 파이썬 딕셔너리로 반환
    """
    # 로컬 변수에 JSON 데이터 정의
    data = {
        "products": [
            {"bank": "신한은행", "amount": "1억원",   "interest": "4%"},
            {"bank": "하나은행", "amount": "1.5억원", "interest": "4.5%"},
            {"bank": "국민은행", "amount": "0.7억원", "interest": "3%"},
            {"bank": "우리은행", "amount": "2억원",   "interest": "3.8%"},
            {"bank": "기업은행", "amount": "1.2억원", "interest": "4.2%"}
        ]
    }
    
    # 필요 시 `day` 매개변수를 이용한 필터링 로직을 추가할 수 있습니다.
    return data

        
@tool
def get_tax_info():
    """
    세율 정보를 조회하는 tool
    
    :return: 로컬 변수에 정의된 JSON 데이터를 파이썬 딕셔너리로 반환
    """
    # 로컬 변수에 JSON 데이터 정의
    data = {
        "tax_rates": [
            {"property_type": "주택", "rate": "1.2%"},
            {"property_type": "오피스텔", "rate": "4.6%"},
            {"property_type": "상가", "rate": "3.5%"},
            {"property_type": "토지", "rate": "2%"}
        ]
    }
    
    return data


class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal[*options]

class State(MessagesState):
    next: str


def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]
    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]
    if goto == "FINISH":
        goto = END

    return Command(goto=goto, update={"next": goto})


loan_manager = create_react_agent(
    llm, tools=[get_loan_product], prompt="당신은 부동산 대출 관리자 입니다. 사용자가 구매하려는 부동산에 가능한 세금 정보를 알려줄 수 있습니다."
)

def loan_manager_node(state: State) -> Command[Literal["supervisor"]]:
    result = loan_manager.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="loan_manager")
            ]
        },
        goto="supervisor",
    )

tax_accountant = create_react_agent(
    llm, tools=[get_tax_info], prompt="You are a tax accountant. You can provide information about tax rates."
)

def tax_accountant_node(state: State) -> Command[Literal["supervisor"]]:
    result = tax_accountant.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="tax_accountant")
            ]
        },
        goto="supervisor",
    )


builder = StateGraph(State)
builder.add_edge(START, "supervisor")
builder.add_node("supervisor", supervisor_node)
builder.add_node("loan_manager", loan_manager_node)
builder.add_node("tax_accountant", tax_accountant_node)

builder.add_edge("loan_manager", "supervisor")
builder.add_edge("tax_accountant", "supervisor")


graph = builder.compile()


try:
    display(Image(graph.get_graph().draw_mermaid_png()))
except Exception:
    # This requires some extra dependencies and is optional
    pass


for s in graph.stream(
    {"messages": [("user", "토지 100억짜리 사려는데 세금과 대출 가능한 상품 알려줘")]},
    {"recursion_limit": 100},
    subgraphs=True
):
    print(s)
    print("----")
