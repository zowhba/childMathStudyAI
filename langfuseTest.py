import openai
from jinja2 import Environment, FileSystemLoader
import os
import uuid
from dotenv import load_dotenv
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-0aac3129-100a-4e8f-bac7-7d66539e16ae",
    secret_key="sk-lf-f12705b9-29ae-4533-a55d-e7831edb36ae",
    host="https://us.cloud.langfuse.com"  # 또는 클라우드 주소
)

# Jinja2 템플릿 로더 설정
template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts')
env = Environment(loader=FileSystemLoader(template_dir))


class  langfuseTest:
    def __init__(self, endpoint, key, dep_curriculum, dep_embed):
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        load_dotenv(dotenv_path)
        openai.api_type = "azure"
        openai.api_base = endpoint
        openai.api_version = "2024-05-01-preview"
        openai.api_key = key
        os.environ["AZURE_OPENAI_API_KEY"] = key
        self.dep_curriculum = dep_curriculum
        self.dep_embed = dep_embed

    def newsTopicTest(self):
        tmpl = env.get_template("prompts/newsTopicTest.txt")
        prompt = tmpl.render("korea")
        
        # Langfuse trace 시작
        trace = langfuse.trace(
            name="wonstablecoin",
            nation_name="korea"  # 필요시 아동 ID 등
        )
        span = trace.span(
            name="openai-newsTopicTest-call",
            input=prompt
        )
        resp = openai.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "피드백 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        output = resp.choices[0].message.content.strip()
        print("[Langfuse Output]", repr(output))  # 값이 정확히 뭔지 확인
        span.output = str(output)  # 혹시 모르니 str로 변환
        span.end()
        return output

if __name__ == "__main__":
    # 테스트용 더미 파라미터 (실제 환경에 맞게 수정 필요)
    endpoint = "https://your-azure-endpoint.openai.azure.com/"
    key = "your-azure-api-key"
    dep_curriculum = "your-model-name"
    dep_embed = "your-embedding-model"
    tester = langfuseTest(endpoint, key, dep_curriculum, dep_embed)
    result = tester.newsTopicTest()
    print("newsTopicTest 결과:", result)

  