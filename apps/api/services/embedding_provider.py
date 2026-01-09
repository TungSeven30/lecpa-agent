"""Embedding provider using sentence-transformers with BGE models."""

from functools import lru_cache

import structlog
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from shared.config import load_embeddings_config
from shared.config.schemas import EmbeddingsConfig

logger = structlog.get_logger()


class EmbeddingProvider:
    """Provider for generating text embeddings.

    Uses sentence-transformers with BGE models for local embedding generation.
    """

    def __init__(self, config: EmbeddingsConfig) -> None:
        """Initialize the embedding provider.

        Args:
            config: Embeddings configuration
        """
        self.config = config
        self._model: SentenceTransformer | None = None

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.config.dimension

    def _get_model(self) -> SentenceTransformer:
        """Get or initialize the sentence transformer model."""
        if self._model is None:
            logger.info(
                "Loading embedding model",
                model=self.config.model,
                device=self.config.device,
            )
            self._model = SentenceTransformer(
                self.config.model,
                device=self.config.device,
                cache_folder=self.config.cache_folder,
            )
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model = self._get_model()

        # Add query prefix for better retrieval (BGE models benefit from this)
        if self.config.query_prefix:
            texts = [f"{self.config.query_prefix}{text}" for text in texts]

        logger.debug("Generating embeddings", count=len(texts))

        embeddings = model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=self.config.show_progress and len(texts) > 10,
        )

        return embeddings.tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for documents (without query prefix).

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model = self._get_model()

        logger.debug("Generating document embeddings", count=len(texts))

        embeddings = model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=self.config.show_progress and len(texts) > 10,
        )

        return embeddings.tolist()

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Embedding vector
        """
        embeddings = await self.embed([query])
        return embeddings[0]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Get cached embedding provider instance."""
    config = load_embeddings_config()
    return EmbeddingProvider(config)
