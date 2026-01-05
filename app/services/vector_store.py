import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# READING PDF AND CHOPPING TEXT
class VectorStoreManager:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


        current_dir = os.path.dirname(os.path.abspath(__file__)) # app/services
        project_root = os.path.abspath(os.path.join(current_dir, "../.."))

        self.base_data_path = os.path.join(project_root, "data")
        self.persist_directory = os.path.join(self.base_data_path, "chroma_db")
        self.kb_path = os.path.join(self.base_data_path, "knowledge_base")

        os.makedirs(self.kb_path, exist_ok=True)

    def ingest_pdfs(self):
        """
        Reads PDFs, but ONLY adds files that are not already in the database.
        """
        if not os.path.exists(self.kb_path):
            print(f"[ERROR] Path {self.kb_path} does not exist.")
            return

        # 1. Получаем список всех PDF в папке
        pdf_files = [f for f in os.listdir(self.kb_path) if f.endswith(".pdf")]

        if not pdf_files:
            print(f"[RAG] No PDF files found in {self.kb_path}!")
            return

        # 2. Инициализируем или загружаем существующую базу
        vector_db = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

        # 3. Проверяем, какие файлы уже есть в базе (через метаданные)
        existing_docs = vector_db.get()
        # Извлекаем уникальные имена файлов из метаданных
        indexed_sources = set()
        if existing_docs and 'metadatas' in existing_docs:
            for meta in existing_docs['metadatas']:
                source = meta.get('source')
                if source:
                    indexed_sources.add(os.path.basename(source))

        new_docs = []
        for file in pdf_files:
            if file in indexed_sources:
                print(f"⏩ [RAG] Skipping '{file}' - already indexed.")
                continue

            print(f"📥 [RAG] Processing NEW file: {file}...")
            loader = PyMuPDFLoader(os.path.join(self.kb_path, file))
            new_docs.extend(loader.load())

        # 4. Если есть новые документы — нарезаем и добавляем
        if new_docs:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = text_splitter.split_documents(new_docs)

            print(f"⚙️ [RAG] Adding {len(chunks)} new chunks to ChromaDB...")
            vector_db.add_documents(chunks)
            print(f"✅ SUCCESS: Vector store updated.")
        else:
            print("Zzz... No new knowledge to add.")

        return vector_db

    def get_retriever(self):
        """
        Returns a retriever object for semantic search queries.
        """
        if not os.path.exists(self.persist_directory):
            print("[ERROR] Vector database not found. Please run ingestion first.")
            return None

        vector_db = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        return vector_db.as_retriever(search_kwargs={"k": 3})