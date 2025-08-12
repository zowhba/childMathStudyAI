"""
RAG (Retrieval-Augmented Generation) 서비스
PDF 문서와 JSON 데이터를 ChromaDB에 임베딩하여 저장하고, 유사도 검색을 제공합니다.
"""

import json
import os
from typing import List, Dict, Any, Optional
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.vector_db_service import VectorDBService
from app.services.azure_openai_service import AzureOpenAIService


class RAGService:
    def __init__(self, vector_service: VectorDBService, azure_service: AzureOpenAIService):
        self.vector_service = vector_service
        self.azure_service = azure_service
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def initialize_rag_data(self) -> bool:
        """
        애플리케이션 시작시 PDF와 JSON 데이터를 ChromaDB에 임베딩하여 저장
        ChromaDB가 비어있을 때만 임베딩 수행 (비용 절약)
        """
        try:
            # 기존 컬렉션 확인
            needs_pdf_embedding = self._needs_pdf_embedding()
            needs_json_embedding = self._needs_json_embedding()
            
            if not needs_pdf_embedding and not needs_json_embedding:
                print("🔄 기존 RAG 데이터 발견, 임베딩 건너뛰기 (비용 절약)")
                return True
            
            print(f"📊 RAG 초기화 필요: PDF={needs_pdf_embedding}, JSON={needs_json_embedding}")
            
            # PDF 파일 임베딩 (필요한 경우만)
            pdf_success = True
            if needs_pdf_embedding:
                if needs_pdf_embedding == "delete_and_recreate":
                    self._clear_pdf_collection()
                pdf_success = self._embed_pdf_file()
                if not pdf_success:
                    print("⚠️  PDF 임베딩 실패 (Azure OpenAI 설정 확인 필요), but continuing...")
            
            # JSON 파일 임베딩 (필요한 경우만)
            json_success = True
            if needs_json_embedding:
                if needs_json_embedding == "delete_and_recreate":
                    self._clear_json_collection()
                json_success = self._embed_curriculum_json()
                if not json_success:
                    print("⚠️  JSON 임베딩 실패 (Azure OpenAI 설정 확인 필요), but continuing...")
            
            # 결과 출력
            if pdf_success and json_success:
                print("✅ RAG 시스템 초기화 완료")
                return True
            else:
                print(f"⚠️  RAG 시스템 부분 초기화 (PDF: {pdf_success}, JSON: {json_success})")
                return pdf_success or json_success
            
        except Exception as e:
            print(f"RAG 데이터 초기화 실패: {e}")
            return False
    
    def _needs_pdf_embedding(self):
        """PDF 임베딩이 필요한지 확인"""
        try:
            collection = self.vector_service.client.get_collection("math_curriculum_guide")
            count = collection.count()
            if count > 0:
                print(f"📚 기존 PDF 가이드 데이터 발견: {count}개 청크")
                return False
            else:
                return "delete_and_recreate"
        except Exception:
            print("📚 PDF 가이드 컬렉션 없음, 새로 생성 필요")
            return True
    
    def _needs_json_embedding(self):
        """JSON 임베딩이 필요한지 확인"""
        try:
            collection = self.vector_service.client.get_collection("curriculum_units")
            count = collection.count()
            if count > 0:
                print(f"📖 기존 교육과정 데이터 발견: {count}개 단원")
                return False
            else:
                return "delete_and_recreate"
        except Exception:
            print("📖 교육과정 컬렉션 없음, 새로 생성 필요")
            return True
    
    def _clear_pdf_collection(self):
        """PDF 컬렉션만 삭제"""
        try:
            self.vector_service.client.delete_collection("math_curriculum_guide")
            print("🗑️  기존 PDF 컬렉션 삭제")
        except Exception as e:
            print(f"PDF 컬렉션 삭제 실패: {e}")
    
    def _clear_json_collection(self):
        """JSON 컬렉션만 삭제"""
        try:
            self.vector_service.client.delete_collection("curriculum_units")
            print("🗑️  기존 JSON 컬렉션 삭제")
        except Exception as e:
            print(f"JSON 컬렉션 삭제 실패: {e}")
    
    def _clear_rag_collections(self):
        """기존 RAG 컬렉션들을 삭제 (사용하지 않음 - 하위 호환성)"""
        self._clear_pdf_collection()
        self._clear_json_collection()
    
    def _embed_pdf_file(self) -> bool:
        """Math_curriculum_guid.pdf 파일을 청크로 나누어 임베딩"""
        try:
            pdf_path = "resource/Math_curriculum_guid.pdf"
            if not os.path.exists(pdf_path):
                print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
                return False
            
            # PDF 텍스트 추출
            text_content = self._extract_pdf_text(pdf_path)
            if not text_content.strip():
                print("PDF에서 텍스트를 추출할 수 없습니다")
                return False
            
            # 텍스트를 청크로 분할
            chunks = self.text_splitter.split_text(text_content)
            
            # ChromaDB 컬렉션 생성
            collection = self.vector_service.client.create_collection(
                name="math_curriculum_guide",
                metadata={"description": "수학 교육과정 가이드 문서"}
            )
            
            # 각 청크를 임베딩하여 저장
            successful_embeds = 0
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # 빈 청크 제외
                    try:
                        embedding = self.azure_service.get_embedding(chunk)
                        collection.add(
                            embeddings=[embedding],
                            documents=[chunk],
                            metadatas=[{
                                "source": "Math_curriculum_guid.pdf",
                                "chunk_id": i,
                                "content_type": "curriculum_guide"
                            }],
                            ids=[f"guide_chunk_{i}"]
                        )
                        successful_embeds += 1
                    except Exception as embed_error:
                        print(f"청크 {i} 임베딩 실패: {embed_error}")
                        continue
            
            print(f"PDF 임베딩 완료: {successful_embeds}개 청크 저장 (총 {len(chunks)}개 중)")
            return successful_embeds > 0
            
        except Exception as e:
            print(f"PDF 임베딩 실패: {e}")
            return False
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF 텍스트 추출 실패: {e}")
            return ""
    
    def _embed_curriculum_json(self) -> bool:
        """curriculum.json 데이터를 단원별로 임베딩"""
        try:
            json_path = "resource/curriculum.json"
            if not os.path.exists(json_path):
                print(f"JSON 파일을 찾을 수 없습니다: {json_path}")
                return False
            
            # JSON 데이터 로드
            with open(json_path, 'r', encoding='utf-8') as file:
                curriculum_data = json.load(file)
            
            # ChromaDB 컬렉션 생성
            collection = self.vector_service.client.create_collection(
                name="curriculum_units",
                metadata={"description": "학년별 학기별 교육과정 단원 정보"}
            )
            
            # 각 학년/학기/단원을 임베딩하여 저장
            doc_id = 0
            for item in curriculum_data:
                grade = item.get("grade")
                semester = item.get("semester") 
                subjects = item.get("subjects", [])
                
                for subject in subjects:
                    # 단원 정보를 텍스트로 구성
                    unit_text = f"{grade}학년 {semester}학기 수학 단원: {subject}"
                    
                    try:
                        # 임베딩 생성
                        embedding = self.azure_service.get_embedding(unit_text)
                        
                        collection.add(
                            embeddings=[embedding],
                            documents=[unit_text],
                            metadatas=[{
                                "grade": grade,
                                "semester": semester,
                                "unit": subject,
                                "source": "curriculum.json"
                            }],
                            ids=[f"unit_{doc_id}"]
                        )
                        doc_id += 1
                    except Exception as embed_error:
                        print(f"임베딩 생성 실패 ({unit_text}): {embed_error}")
                        continue
            
            print(f"Curriculum JSON 임베딩 완료: {doc_id}개 단원 저장")
            return doc_id > 0
            
        except Exception as e:
            print(f"JSON 임베딩 실패: {e}")
            return False
    
    def search_curriculum_guide(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        수학 교육과정 가이드에서 유사도 검색
        """
        try:
            collection = self.vector_service.client.get_collection("math_curriculum_guide")
            query_embedding = self.azure_service.get_embedding(query)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    search_results.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            return search_results
            
        except Exception as e:
            print(f"교육과정 가이드 검색 실패: {e}")
            return []
    
    def get_curriculum_units(self, grade: int, semester: int) -> List[str]:
        """
        특정 학년/학기의 교육과정 단원 목록 반환
        """
        try:
            collection = self.vector_service.client.get_collection("curriculum_units")
            
            # 메타데이터 필터링으로 해당 학년/학기 단원 검색
            results = collection.get(
                where={
                    "$and": [
                        {"grade": {"$eq": grade}},
                        {"semester": {"$eq": semester}}
                    ]
                },
                include=["metadatas"]
            )
            
            units = []
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    units.append(metadata["unit"])
            
            return units
            
        except Exception as e:
            print(f"ChromaDB에서 교육과정 단원 검색 실패: {e}")
            # Fallback: JSON 파일에서 직접 읽기
            return self._get_curriculum_units_from_json(grade, semester)
    
    def _get_curriculum_units_from_json(self, grade: int, semester: int) -> List[str]:
        """JSON 파일에서 직접 교육과정 단원 읽기 (fallback)"""
        try:
            import json
            json_path = "resource/curriculum.json"
            with open(json_path, 'r', encoding='utf-8') as file:
                curriculum_data = json.load(file)
            
            for item in curriculum_data:
                if item.get("grade") == grade and item.get("semester") == semester:
                    return item.get("subjects", [])
            
            return []
        except Exception as e:
            print(f"JSON 파일에서 교육과정 단원 읽기 실패: {e}")
            return []
    
    def search_unit_guide(self, unit_name: str, grade: int, semester: int, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        특정 단원에 대한 가이드 문서 검색
        """
        try:
            # 검색 쿼리 구성
            query = f"{grade}학년 {semester}학기 수학 {unit_name} 단원 문제 출제 가이드 교육과정"
            
            results = self.search_curriculum_guide(query, top_k)
            if results:
                return results
            else:
                print(f"PDF 가이드 검색 결과 없음: {unit_name}")
                return []
                
        except Exception as e:
            print(f"단원 가이드 검색 실패: {e}")
            return []
