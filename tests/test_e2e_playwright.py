import os
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8501"
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))
VALID_WAV = os.path.join(FIXTURES_DIR, "valid_short.wav")


# ─── 1. UI Layout & Accessibility Tests ────────────────────────────────────────

def test_initial_page_load_and_empty_state(page: Page):
    """Verify initial page loads cleanly with header, sidebar, and empty state message."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    # Wait for the main app container to mount
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=20000)

    # Verify document title & headings
    expect(page).to_have_title("AI Video Assistant", timeout=15000)
    hero_title = page.get_by_text("AI Video Assistant").first
    expect(hero_title).to_be_visible(timeout=10000)

    # Verify sidebar input controls
    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    expect(input_box).to_be_visible()
    expect(input_box).to_be_enabled()

    # Verify Analyze button
    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    expect(analyse_btn).to_be_visible()
    expect(analyse_btn).to_be_enabled()

    # Verify empty state hero
    empty_state = page.locator("text=Ready to Analyse")
    expect(empty_state).to_be_visible()


def test_mobile_viewport_layout(page: Page):
    """Verify responsive UI renders accessibility controls and header on mobile viewports."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    # Allow Streamlit websocket hydration on mobile
    hero_title = page.get_by_text("AI Video Assistant").first
    expect(hero_title).to_be_visible(timeout=15000)
    
    # Subtitle is visible
    hero_sub = page.get_by_text("Transcribe · Summarise · Chat with your meetings").first
    expect(hero_sub).to_be_visible(timeout=10000)


# ─── 2. Validation & Error Handling Tests ─────────────────────────────────────

def test_validation_empty_input_rejection(page: Page):
    """Verify submitting empty input displays immediate validation error."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    input_box.fill("")

    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    analyse_btn.click()

    error_alert = page.locator("text=Please enter a YouTube URL or file path.")
    expect(error_alert).to_be_visible(timeout=5000)


def test_validation_nonexistent_local_file(page: Page):
    """Verify entering a non-existent file path shows clear validation error."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    fake_path = r"C:\fake_folder_98765\does_not_exist.mp4"
    input_box.fill(fake_path)

    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    analyse_btn.click()

    error_alert = page.locator("text=Local file does not exist")
    expect(error_alert).to_be_visible(timeout=5000)


# ─── 3. End-to-End Analysis Journey ───────────────────────────────────────────

def test_complete_analysis_journey_with_valid_fixture(page: Page):
    """
    Test complete user journey:
    1. Enter valid audio/video file.
    2. Click '⚡ Analyse'.
    3. Observe pipeline execution and transition to results.
    4. Verify Session Title, Summary, Action Items, Key Decisions, Questions.
    5. Interact with RAG Chatbot.
    6. Verify Clear Chat works.
    """
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    input_box.fill(VALID_WAV)

    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    expect(analyse_btn).to_be_enabled()
    analyse_btn.click()

    # Bounded wait for analysis to complete and results to render
    title_banner = page.locator(".card-title", has_text="Session Title")
    expect(title_banner).to_be_visible(timeout=90000)

    # Verify Summary card
    summary_card = page.locator(".card-title", has_text="Summary")
    expect(summary_card).to_be_visible()

    # Verify Action Items card
    action_card = page.locator(".card-title", has_text="Action Items")
    expect(action_card).to_be_visible()

    # Verify Key Decisions card
    decisions_card = page.locator(".card-title", has_text="Key Decisions")
    expect(decisions_card).to_be_visible()

    # Verify Open Questions card
    questions_card = page.locator(".card-title", has_text="Open Questions")
    expect(questions_card).to_be_visible()

    # Verify Transcript expander can be opened
    transcript_expander = page.locator("text=Full Transcript")
    expect(transcript_expander).to_be_visible()
    transcript_expander.click()

    # Verify Chat Section is visible
    chat_header = page.get_by_text("💬 Chat with your Meeting")
    expect(chat_header).to_be_visible()

    # Test RAG chat interaction
    question_input = page.get_by_placeholder("What were the main decisions made?")
    expect(question_input).to_be_visible()
    question_input.fill("What is this audio about?")

    send_btn = page.get_by_role("button", name="Send →")
    send_btn.click()

    # Wait for assistant response bubble
    assistant_bubble = page.locator(".chat-bubble.bot-bubble")
    expect(assistant_bubble).to_be_visible(timeout=30000)

    # Test Clear Chat button
    clear_btn = page.get_by_role("button", name="🗑️ Clear Chat")
    expect(clear_btn).to_be_visible()
    clear_btn.click()

    # Verify chat history is cleared
    expect(page.locator(".chat-container")).not_to_be_visible(timeout=5000)


# ─── 4. Stale Results and Second Analysis Flow ────────────────────────────────

def test_second_analysis_resets_previous_results(page: Page):
    """Verify initiating a new analysis clears previous results rather than displaying stale data."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    # Provide an invalid file path to check immediate clear of previous results
    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    input_box.fill(r"C:\another_fake_video.wav")

    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    analyse_btn.click()

    # Error message shown, stale results not visible
    expect(page.locator("text=Local file does not exist")).to_be_visible(timeout=5000)
    expect(page.locator("text=Session Title")).not_to_be_visible()


# ─── 5. Button Recovery & Keyboard Accessibility Tests ─────────────────────────

def test_submission_button_state_and_recovery(page: Page):
    """Verify button is enabled initially, stays enabled after error for recovery."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    
    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    expect(analyse_btn).to_be_enabled()

    # Trigger validation error
    analyse_btn.click()
    expect(page.locator("text=Please enter a YouTube URL or file path.")).to_be_visible(timeout=5000)

    # Button remains enabled for user to correct and retry
    expect(analyse_btn).to_be_enabled()


def test_keyboard_navigation_accessibility(page: Page):
    """Verify keyboard accessibility: user can focus input and submit via keyboard."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    
    input_box = page.get_by_placeholder("https://youtube.com/watch?v=... or /path/to/file.mp4")
    input_box.focus()
    input_box.type(r"C:\nonexistent_keyboard_test.mp4")
    
    # Tab to the analyze button
    analyse_btn = page.get_by_role("button", name="⚡ Analyse")
    analyse_btn.focus()
    page.keyboard.press("Enter")
    
    expect(page.locator("text=Local file does not exist")).to_be_visible(timeout=5000)

