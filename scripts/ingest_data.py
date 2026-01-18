from app.services.vector_store import VectorStoreManager

# START PROCESSING OF READING PDF


def main():
    print("🚀 Starting PDF ingestion process...")
    manager = VectorStoreManager()
    manager.ingest_pdfs()


if __name__ == "__main__":
    main()
