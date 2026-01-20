# --- UNIT AND INTEGRATIONAL TEST  RAG ---


import os
import pytest
import allure
from unittest.mock import MagicMock, patch
from app.services.vector_store import VectorStoreManager


@allure.feature("RAG Infrastructure")
@pytest.mark.asyncio
class TestVectorStoreManager:

    @allure.story("Initialization")
    @allure.description("Verify that the manager correctly sets up paths for ChromaDB and Knowledge Base.")
    def test_1_init_paths(self, vsm):
        """TEST 1: Check Directory Setup."""
        with allure.step("Validating internal manager paths"):
            allure.attach(vsm.persist_directory, name="Persist Directory", attachment_type=allure.attachment_type.TEXT)
            allure.attach(vsm.kb_path, name="Knowledge Base Path", attachment_type=allure.attachment_type.TEXT)

            assert "chroma_db" in vsm.persist_directory, "ChromaDB path is incorrect!"
            assert "knowledge_base" in vsm.kb_path, "Knowledge Base path is incorrect!"

    @allure.story("Ingestion Logic")
    @allure.description("Verify system behavior when the knowledge base directory is empty.")
    def test_2_ingest_pdfs_no_files(self, vsm):
        """TEST 2: Execute ingestion with empty folder."""
        with patch("os.path.exists", return_value=True), \
                patch("os.listdir", return_value=[]):
            with allure.step("Running ingest_pdfs()"):
                result = vsm.ingest_pdfs()

            with allure.step("Checking result: Should be None"):
                assert result is None, "Result should be None when no files exist"

    @allure.story("Ingestion Logic")
    @allure.description("Check that the manager does not re-process files already present in ChromaDB.")
    def test_3_ingest_pdfs_skips_existing(self, vsm):
        """TEST 3: Skip Already Indexed Files."""
        mock_db = MagicMock()
        mock_db.get.return_value = {
            "metadatas": [{"source": "path/to/existing.pdf"}]
        }

        with patch("os.path.exists", return_value=True), \
                patch("os.listdir", return_value=["existing.pdf"]), \
                patch("app.services.vector_store.Chroma", return_value=mock_db), \
                patch("app.services.vector_store.PyMuPDFLoader") as mock_loader:
            with allure.step("Running ingestion for existing file"):
                vsm.ingest_pdfs()

            with allure.step("Verifying Loader state"):

                assert mock_loader.called is False, "Error loader is runinng but book is exist!"

    @allure.story("Ingestion Logic")
    @allure.title("TEST 4: New File Ingestion")
    @allure.description("Validate the complete data flow: PDF Loading -> Metadata Attachment -> Database Injection.")
    def test_4_ingest_pdfs_success(self, vsm):
        """
        Verify that new PDF files are correctly processed and stored in ChromaDB
        with the appropriate content and source metadata.
        """
        # Import the real Document class to ensure type matching between the test and the service
        from langchain_core.documents import Document

        # 1. SETUP: Create a Mock for the Vector Database to track method calls
        mock_db = MagicMock()

        # Simulate an empty database by returning no metadata, forcing the ingestion to trigger
        mock_db.get.return_value = {"metadatas": []}

        # Define the sample text and create a real Document object as the expected payload
        test_docs = [
            Document(
                page_content="Planetary periods analysis",
                metadata={"source": "new_book.pdf"}
            )
        ]

        # 2. ISOLATION: Use patch to mock external system dependencies (OS and LangChain)
        # Mocking exists and listdir prevents the code from accessing your real folders
        with patch("os.path.exists", return_value=True), \
                patch("os.listdir", return_value=["new_book.pdf"]), \
                patch("app.services.vector_store.Chroma", return_value=mock_db), \
                patch("app.services.vector_store.PyMuPDFLoader") as mock_loader_class:
            # Setup the mocked loader instance (the 'fake' object created by the class)
            mock_instance = mock_loader_class.return_value

            # Configure the .load() method to return our pre-defined test documents immediately
            mock_instance.load.return_value = test_docs

            # Execute the actual service logic inside the virtualized environment
            with allure.step("Executing ingestion for a new PDF file"):
                vsm.ingest_pdfs()

            # 3. VERIFICATION: Check if the database received the correct data
            with allure.step("Final Check: Is the book in the DB?"):
                # Assert that add_documents was called with the exact Document objects we provided
                mock_db.add_documents.assert_called_with(test_docs)


    @allure.story("Retriever Logic")
    @allure.description("Base of knoledgw is empty so no searh.")
    def test_5_get_retriever_missing_db(self, vsm):
        """TEST 5: Error handling if DB is missing."""
        with patch("os.path.exists", return_value=False):
            with allure.step("Attempting to get retriever"):
                retriever = vsm.get_retriever()

            with allure.step("Checking result"):
                assert retriever is None, "Retriever should be None if DB path doesn't exist"



@allure.feature("RAG Integration")
@pytest.mark.asyncio
class TestRAGIntegration:

    @allure.story("Semantic Search")
    @allure.description("Validates retrieval from multiple PDF sources simultaneously.")
    async def test_6_knowledge_base_multi_source(self):
        """TEST 6: Multi-Source Retrieval Test."""

        with allure.step("Initializing Vector Store Manager"):
            vsm = VectorStoreManager()
            retriever = vsm.get_retriever()
            retriever.search_kwargs = {"k": 15}

        query = "What are the effects of Rahu and planetary periods (Dashas)?"

        with allure.step(f"Sending Semantic Query: {query}"):
            docs = await retriever.ainvoke(query)

        with allure.step("Checking retrieved documents count"):
            allure.attach(str(len(docs)), name="Total Chunks Found", attachment_type=allure.attachment_type.TEXT)
            assert len(docs) > 0, "RAG Error: No documents retrieved!"

        with allure.step("Extracting and Validating Sources"):
            sources = set([os.path.basename(d.metadata.get("source", "unknown")) for d in docs])
            allure.attach(", ".join(sources), name="Identified Sources", attachment_type=allure.attachment_type.TEXT)

            assert len(sources) >= 1, "No source metadata found!"

        with allure.step("Content Sample Validation"):
            for source in sources:
                sample_doc = next(d for d in docs if os.path.basename(d.metadata.get("source", "")) == source)
                allure.attach(
                    sample_doc.page_content[:300],
                    name=f"Sample from {source}",
                    attachment_type=allure.attachment_type.TEXT
                )

            assert any(len(d.page_content) > 10 for d in docs), "Retrieved content is too short!"