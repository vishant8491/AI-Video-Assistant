import os
import pytest
from unittest.mock import patch, MagicMock

from utils.audio_processor import process_input, convert_to_wav, chunk_audio
from core.llm_factory import get_llm
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.summarizer import generate_title, summarize
from core.vector_store import build_vector_store, get_retriever
from core.transcriber import transcribe_chunk

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
VALID_WAV = os.path.join(FIXTURES_DIR, "valid_short.wav")
EMPTY_WAV = os.path.join(FIXTURES_DIR, "empty_file.wav")
UNSUPPORTED_TXT = os.path.join(FIXTURES_DIR, "unsupported.txt")
CORRUPT_WAV = os.path.join(FIXTURES_DIR, "corrupt.wav")


# ─── 1. Audio Processor Tests ─────────────────────────────────────────────────

def test_process_input_valid_local_wav():
    """Verify processing a valid local WAV file succeeds and returns chunk paths."""
    assert os.path.exists(VALID_WAV)
    chunks = process_input(VALID_WAV)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert os.path.exists(chunk)
        assert chunk.endswith(".wav")


def test_process_input_missing_file():
    """Verify non-existent local file raises FileNotFoundError with descriptive message."""
    missing_file = os.path.join(FIXTURES_DIR, "does_not_exist_12345.mp4")
    with pytest.raises((FileNotFoundError, Exception)) as exc_info:
        process_input(missing_file)
    assert "not found" in str(exc_info.value).lower() or "no such file" in str(exc_info.value).lower()


def test_process_input_empty_file():
    """Verify empty 0-byte file raises an error rather than hanging or passing silently."""
    assert os.path.exists(EMPTY_WAV)
    with pytest.raises(Exception):
        process_input(EMPTY_WAV)


def test_chunk_audio_duration_boundary():
    """Verify short audio <= chunk_minutes is not unnecessarily multiplied."""
    chunks = chunk_audio(VALID_WAV, chunk_minutes=10)
    assert len(chunks) == 1
    assert os.path.exists(chunks[0])


# ─── 2. LLM Factory Tests ──────────────────────────────────────────────────────

def test_llm_factory_initialization_with_groq():
    """Verify get_llm initializes successfully when GROQ_API_KEY is present."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test1234567890"}):
        llm = get_llm()
        assert llm is not None
        assert "ChatGroq" in type(llm).__name__


def test_llm_factory_error_when_no_keys():
    """Verify ValueError is raised when no LLM API keys are provided in environment."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            get_llm()
        assert "No valid LLM API key" in str(exc_info.value)


# ─── 3. Summarizer & Extractor Tests (with mock LLM) ──────────────────────────

def test_generate_title_mocked():
    """Verify generate_title invokes LLM chain and returns expected title string."""
    from langchain_core.runnables import RunnableLambda
    fake_llm = RunnableLambda(lambda x: "Quarterly Financial Review")

    with patch("core.summarizer.get_llm", return_value=fake_llm):
        title = generate_title("Meeting discussion regarding Q3 budget and targets.")
        assert title == "Quarterly Financial Review"


def test_summarize_mocked():
    """Verify summarize performs map-reduce chunking and returns summary."""
    from langchain_core.runnables import RunnableLambda
    fake_llm = RunnableLambda(lambda x: "- Discussed Q3 budget\n- Approved hiring plan")

    with patch("core.summarizer.get_llm", return_value=fake_llm):
        summary = summarize("The meeting started at 10 AM. We discussed project milestones.")
        assert "- Discussed Q3 budget" in summary


def test_extract_action_items_mocked():
    """Verify extract_action_items returns numbered tasks or fallback."""
    from langchain_core.runnables import RunnableLambda
    fake_llm = RunnableLambda(lambda x: "1. Prepare slide deck - Alice - Friday")

    with patch("core.extractor.get_llm", return_value=fake_llm):
        actions = extract_action_items("Alice will prepare the slide deck by Friday.")
        assert "Alice" in actions and "slide deck" in actions


def test_extract_key_decisions_mocked():
    """Verify extract_key_decisions returns extracted decisions."""
    from langchain_core.runnables import RunnableLambda
    fake_llm = RunnableLambda(lambda x: "1. Migrate to PostgreSQL by Q4")

    with patch("core.extractor.get_llm", return_value=fake_llm):
        decisions = extract_key_decisions("Team decided to migrate to PostgreSQL by Q4.")
        assert "PostgreSQL" in decisions


def test_extract_questions_mocked():
    """Verify extract_questions extracts open questions or fallback."""
    from langchain_core.runnables import RunnableLambda
    fake_llm = RunnableLambda(lambda x: "1. Who will handle the client demo?")

    with patch("core.extractor.get_llm", return_value=fake_llm):
        questions = extract_questions("Who will handle the client demo next Monday?")
        assert "demo" in questions


# ─── 4. Vector Store & RAG Tests ──────────────────────────────────────────────

def test_build_vector_store():
    """Verify Chroma vector store is created from text documents."""
    test_transcript = "Alice presented the Q3 marketing results. ROI increased by 15 percent."
    vs = build_vector_store(test_transcript)
    assert vs is not None

    retriever = get_retriever(vs, k=1)
    docs = retriever.invoke("marketing results")
    assert len(docs) >= 1
    assert "marketing" in docs[0].page_content.lower()
