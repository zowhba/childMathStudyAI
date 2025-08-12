from chromadb import PersistentClient

# ChromaDB가 저장된 경로 (환경변수나 코드에서 지정한 경로와 일치해야 함)
persist_directory = "./chroma_db"  # 실제 경로로 맞추세요

client = PersistentClient(path=persist_directory)

# 모든 컬렉션 이름 출력
collections = client.list_collections()
print("Collections:", [c.name for c in collections])

# 각 컬렉션의 데이터 출력
for collection in collections:
    print(f"\n--- Collection: {collection.name} ---")
    docs = collection.get()
    print(docs)