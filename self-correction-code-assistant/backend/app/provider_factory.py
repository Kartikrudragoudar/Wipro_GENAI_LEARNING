"""Provider factory — creates the correct AIProvider and optional EmbeddingStore based on environment config.

Set AI_PROVIDER in .env to one of: mock, openai, gemini, anthropic
Set EMBEDDING_PROVIDER to: none, openai, gemini (defaults to none for MVP)
"""

import os
import logging

from app.ai_provider import AIProvider
from app.mock_provider import MockAIProvider

logger = logging.getLogger(__name__)


def create_ai_provider() -> AIProvider:
    """Instantiate the AI provider based on AI_PROVIDER env var."""
    provider_name = os.getenv("AI_PROVIDER", "mock").lower().strip()

    if provider_name == "mock":
        logger.info("Using MockAIProvider (no LLM calls).")
        return MockAIProvider()

    from app.llm_provider import LLMProvider

    if provider_name == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
        logger.info("Using OpenAI provider: model=%s", model)
        return LLMProvider(llm)

    if provider_name == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is required when AI_PROVIDER=gemini")
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)
        logger.info("Using Gemini provider: model=%s", model)
        return LLMProvider(llm)

    if provider_name == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is required when AI_PROVIDER=anthropic")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        llm = ChatAnthropic(model=model, temperature=temperature, api_key=api_key)
        logger.info("Using Anthropic provider: model=%s", model)
        return LLMProvider(llm)

    raise ValueError(f"Unknown AI_PROVIDER: '{provider_name}'. Choose from: mock, openai, gemini, anthropic")


def create_embedding_store():
    """Optionally create the embedding store based on EMBEDDING_PROVIDER env var.

    Returns None if embeddings are disabled.
    """
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "none").lower().strip()

    if embedding_provider == "none":
        logger.info("Embeddings disabled (EMBEDDING_PROVIDER=none).")
        return None

    from app.embeddings import CorrectionEmbeddingStore

    if embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        embeddings = OpenAIEmbeddings(model=model, api_key=api_key)
        logger.info("Using OpenAI embeddings: model=%s", model)
        return CorrectionEmbeddingStore(embeddings)

    if embedding_provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=gemini")
        model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        embeddings = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
        logger.info("Using Gemini embeddings: model=%s", model)
        return CorrectionEmbeddingStore(embeddings)

    raise ValueError(f"Unknown EMBEDDING_PROVIDER: '{embedding_provider}'. Choose from: none, openai, gemini")
