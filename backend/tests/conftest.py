"""Conftest: patch Pinecone and Anthropic before any app modules are imported."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# Set env vars before pydantic-settings reads them
os.environ["PINECONE_API_KEY"] = "test-key"
os.environ["ANTHROPIC_API_KEY"] = "test-key"

# Create mock Pinecone module-level objects before app.retrieval is imported
_mock_pc = MagicMock()
_mock_index = MagicMock()
_mock_pc.Index.return_value = _mock_index

# Patch the pinecone.Pinecone class to return our mock
import pinecone
_orig_pinecone = pinecone.Pinecone
pinecone.Pinecone = MagicMock(return_value=_mock_pc)

# Also patch Anthropic client
import anthropic
_orig_anthropic = anthropic.Anthropic
anthropic.Anthropic = MagicMock()
