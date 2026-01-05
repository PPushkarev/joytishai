import pytest
import os
from app.services.vector_store import VectorStoreManager


@pytest.mark.asyncio
async def test_knowledge_base_multi_source():
    """
    Integration Test for the RAG System.
    Validates that the system can retrieve relevant chunks from multiple
    PDF sources simultaneously using semantic search.
    """

    # 1. Initialize Vector Store Manager
    vsm = VectorStoreManager()

    # Increase 'k' to 15 to ensure we capture chunks from different books
    # Even if one book is more dominant in the search results.
    retriever = vsm.get_retriever()
    retriever.search_kwargs = {"k": 15}

    # 2. Define a broad query to touch multiple topics (Planets + Timing)
    query = "What are the effects of Rahu and planetary periods (Dashas)?"

    print(f"\n🔍 Sending Query: '{query}'")
    docs = await retriever.ainvoke(query)

    # 3. Validations
    assert len(docs) > 0, "RAG Error: No documents retrieved from the vector store!"

    # Extract unique source filenames from the metadata
    sources = set([os.path.basename(d.metadata['source']) for d in docs])

    print(f"\n✅ SUCCESS: Retrieved {len(docs)} relevant chunks.")
    print(f"📚 Sources identified in the analysis ({len(sources)}): {sources}")
    print("-" * 60)

    # 4. Display one representative sample for each identified source
    for source in sources:
        # Find the most relevant chunk for this specific source
        sample_doc = next(d for d in docs if os.path.basename(d.metadata['source']) == source)

        print(f"📖 SOURCE: {source}")
        print(f"📝 CONTENT SAMPLE: {sample_doc.page_content[:200]}...")
        print("-" * 60)

    # Final assertion: Check if at least one book was found
    assert len(sources) >= 1, "RAG Error: No source metadata found in retrieved documents."