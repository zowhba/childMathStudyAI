from chromadb import PersistentClient
import os
from app.services.azure_openai_service import AzureOpenAIService
import openai

class VectorDBService:
    def __init__(self, persist_directory):
        self.client = PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="learning")
        # self.dep_curriculum = os.getenv("AZURE_OPENAI_DEPLOY_CURRICULUM")  # Uncomment if needed

    def add_assessment(self, student_id: str, lesson_id: str, responses: list, materials_text: str, azure_service):
        print(f"add_assessment called: student_id={student_id}, lesson_id={lesson_id}, responses={responses}")
        embedding = azure_service.get_embedding(" ".join(responses))
        metadata = {"student_id": student_id, "lesson_id": lesson_id, "type": "assessment", "materials_text": materials_text}
        self.collection.add(
            documents=[" ".join(responses)],
            embeddings=[embedding],
            ids=[f"{student_id}_{lesson_id}_resp"],
            metadatas=[metadata]
        )
        print("add_assessment finished")

    def query_by_grade_semester(self, grade: int, semester: int, top_k: int = 5) -> list:
        """학년/학기 메타데이터로 필터링하여 자료 조회 (임베딩 불필요)"""
        where = {"$and": [{"grade": grade}, {"semester": semester}]}
        res = self.collection.get(where=where)
        documents = res.get("documents", []) or []
        metadatas = res.get("metadatas", []) or []
        # 길이 정렬 및 상한 적용
        length = min(len(documents), len(metadatas), top_k)
        return list(zip(documents[:length], metadatas[:length]))

    def create_feedback(self, prompt: str):
        resp = openai.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "다음 교재 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        # This method should return the response from the OpenAI chat completion
        return resp

    def get_latest_assessment(self, student_id: str):
        """특정 학생의 가장 최근 평가 응답을 반환"""
        where = {
            "$and": [
                {"student_id": student_id},
                {"type": "assessment"}
            ]
        }
        results = self.collection.get(where=where)
        if not results["ids"]:
            return None
        latest_idx = -1
        return {
            "responses": results["documents"][latest_idx],
            "metadata": results["metadatas"][latest_idx]
        }