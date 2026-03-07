from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pinecone_api_key: str
    anthropic_api_key: str
    pinecone_index_name: str = "lazlow"
    pinecone_namespace: str = "hansard"

    # Retrieval defaults
    search_top_k: int = 20
    rerank_top_n: int = 10
    rerank_model: str = "cohere-rerank-3.5"
    embedding_model: str = "llama-text-embed-v2"

    # Generation
    generation_model: str = "claude-opus-4-20250514"
    max_tokens: int = 4096

    model_config = {"env_file": ".env"}


settings = Settings()
