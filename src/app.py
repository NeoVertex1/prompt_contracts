"""
Enhanced Chat‑to‑PDF application using Gemini 2.5 Flash via Gradio.

This script implements a polished web interface that allows users to
upload a PDF and supply a Gemini API key. The application then
extracts text from the PDF, combines it with a detailed reasoning
contract, and queries the Gemini 2.5 Flash model about the document.

Key features:
  • Only the final answer from the model's JSON response is displayed
    in the chat.  
  • The full JSON responses are stored verbatim for developer
    inspection.  
  • Structured logs, including evidence, reasoning and metadata
    extracted from the JSON, are maintained for each answer.  
  • A separate Logs tab presents both structured and raw output with a
    refresh button.  
  • A clean, tabbed interface with icons helps orient the user.

Dependencies:
  - gradio
  - PyPDF2
  - google‑genai (>=1.0.0) or google‑generativeai (<1.0.0)

If these packages are missing, the app will not crash but will prompt
the user accordingly. Install dependencies with pip, for example:

```
pip install gradio PyPDF2 google-genai
```
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, List, Tuple, Dict, Any

try:
    import gradio as gr  # type: ignore
except ImportError as e:
    raise ImportError(
        "Gradio is required to run this application. Install it via pip: "
        "pip install gradio"
    ) from e

# Try to import PyPDF2 for PDF text extraction.
try:
    from PyPDF2 import PdfReader  # type: ignore
except ImportError:
    PdfReader = None  # type: ignore[assignment]

# Attempt to import Gemini API clients. Prefer google-genai if available.
try:
    from google import genai  # type: ignore
except ImportError:
    genai = None  # type: ignore[assignment]
try:
    import google.generativeai as generativeai  # type: ignore
except ImportError:
    generativeai = None  # type: ignore[assignment]

# Set up logging for debugging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the universal v4 prompt contract. This file must be present in the
# same directory as this script.
CONTRACT_PATH = Path(__file__).parent / "universal_v4_contract.xml"
if not CONTRACT_PATH.exists():
    raise FileNotFoundError(f"Prompt contract file not found at {CONTRACT_PATH}")
with open(CONTRACT_PATH, "r", encoding="utf-8") as fp:
    PROMPT_CONTRACT: str = fp.read()

# Global state for the application. In a multi‑user environment you'd
# scope these to individual sessions.
pdf_text_content: str = ""
api_key: str = ""
gemini_call: Callable[[str], str] | None = None
conversation_logs: List[str] = []
answer_json_log: List[str] = []
answer_structured_log: List[Dict[str, Any]] = []


def parse_pdf(file_obj) -> str:
    """
    Extract text from a PDF using PyPDF2.

    If PyPDF2 is not installed or an error occurs, a descriptive
    message is returned instead.
    """
    if file_obj is None:
        return ""
    if PdfReader is None:
        return (
            "PyPDF2 is not installed. Please install it via pip to enable "
            "PDF parsing."
        )
    try:
        reader = PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text
    except Exception as exc:
        logger.exception("Error parsing PDF", exc_info=exc)
        return f"Error parsing PDF: {exc}"


def init_gemini_client(provided_key: str) -> Callable[[str], str]:
    """
    Initialise and return a function that calls the Gemini API using
    the provided API key. Attempts to use google-genai first, then
    google-generativeai, falling back to a stub if both are unavailable.
    """
    global api_key
    api_key = provided_key
    if not provided_key:
        raise ValueError("API key is required to initialise the Gemini client.")

    if genai is not None:
        def call_with_genai(messages: str) -> str:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=messages,
            )
            return response.text
        return call_with_genai

    if generativeai is not None:
        generativeai.configure(api_key=api_key)
        model = generativeai.GenerativeModel("gemini-2.5-flash")
        def call_with_generativeai(messages: str) -> str:
            response = model.generate_content(messages)
            return response.text
        return call_with_generativeai

    def call_stub(_messages: str) -> str:
        return (
            "Neither google‑genai nor google‑generativeai is installed. "
            "Please install one of these packages to enable Gemini API calls."
        )
    return call_stub


def upload_and_prepare(pdf_file, user_api_key: str) -> str:
    """
    Handle PDF upload and API key input. Extracts text from the PDF and
    initialises the Gemini API client.
    """
    global pdf_text_content, gemini_call
    if pdf_file is None:
        return "Please upload a PDF file."
    if not user_api_key:
        return "Please provide your Gemini API key."
    pdf_text_content = parse_pdf(pdf_file)
    if not pdf_text_content:
        return "Failed to parse PDF or PDF contained no extractable text."
    gemini_call = init_gemini_client(user_api_key)
    conversation_logs.append(
        json.dumps({"event": "initialised", "message": "Loaded PDF and API key"}, ensure_ascii=False)
    )
    return "PDF loaded and API key set. You can now ask questions about the document."


def chat(user_message: str, history: List[Tuple[str, str]]):
    """
    Process a user question: send the prompt to Gemini and update
    history with only the final answer. Store the full JSON and
    structured logs for developer inspection.

    Returns three values: the updated chat history, an empty string to
    clear the input box, and a newline‑separated string of all raw JSON
    outputs. The third return value enables live streaming of the raw
    model output in the "Raw View" tab.
    """
    global gemini_call
    if not pdf_text_content:
        history.append((user_message, "Please upload a PDF and set your API key before asking questions."))
        return history, ""
    if not api_key:
        history.append((user_message, "API key is missing. Please upload a PDF and provide your key first."))
        return history, ""
    # Compose the prompt: contract + document context + user question
    system_prompt = PROMPT_CONTRACT
    document_context = f"Document contents:\n{pdf_text_content}\n"
    messages_for_api = "\n".join([
        system_prompt,
        document_context,
        user_message,
    ])
    try:
        model_output = gemini_call(messages_for_api) if gemini_call else "Gemini client is not initialised."
    except Exception as exc:
        logger.exception("Error calling Gemini API", exc_info=exc)
        model_output = f"Error calling Gemini API: {exc}"
    final_answer: str | None = None
    if isinstance(model_output, str):
        stripped = model_output.strip()
        # Remove fenced code blocks (e.g., ```json ... ```)
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if "\n" in stripped:
                stripped = stripped.split("\n", 1)[1]
        try:
            parsed = json.loads(stripped)
            final_answer = parsed.get("answer")
            answer_json_log.append(stripped)
            answer_structured_log.append(parsed)
        except Exception:
            # If parsing fails, store the raw output and use it as the answer
            answer_json_log.append(stripped)
            answer_structured_log.append({"raw": stripped})
    if final_answer is None:
        final_answer = model_output if isinstance(model_output, str) else str(model_output)
    conversation_logs.append(json.dumps({"user": user_message, "answer": final_answer}, ensure_ascii=False))
    history.append((user_message, final_answer))
    # Build the raw stream by concatenating all raw JSON outputs. This will be
    # displayed in the "Raw View" tab for real‑time monitoring.
    raw_stream = "\n".join(answer_json_log)
    return history, "", raw_stream


def view_logs() -> str:
    """
    Provide a fallback raw log view if structured logs are unavailable.
    """
    if answer_json_log:
        return "\n".join(answer_json_log)
    if conversation_logs:
        return "\n".join(conversation_logs)
    return "No logs available yet."


def get_structured_logs() -> List[Dict[str, Any]]:
    """
    Return the list of parsed JSON outputs.
    """
    return answer_structured_log


def get_raw_logs() -> str:
    """
    Return the raw JSON outputs as a single newline separated string.
    """
    return "\n".join(answer_json_log) if answer_json_log else ""


def build_interface() -> gr.Blocks:
    """
    Build the Gradio interface with a Chat tab and a Logs tab.
    """
    with gr.Blocks(title="Gemini Chat‑to‑PDF App") as demo:
        gr.Markdown(
            """
            # Chat to PDF with Gemini 2.5 Flash

            Upload a PDF and provide your Gemini API key to ask questions
            about the document. The model applies a detailed reasoning
            protocol defined in the prompt contract and returns a structured
            JSON response. Only the final answer is shown here; visit the
            **Logs** tab to inspect the full outputs and other details.
            """
        )
        with gr.Tabs() as tabs:
            with gr.Tab("Chat"):
                with gr.Row():
                    pdf_input = gr.File(label="📄 PDF Document", file_types=[".pdf"], scale=1)
                    api_key_input = gr.Textbox(
                        label="🔑 API Key",
                        type="password",
                        placeholder="Enter your API key here",
                        scale=1,
                    )
                    upload_button = gr.Button("Setup", variant="primary", scale=1)
                status_output = gr.Textbox(
                    label="Status", value="", interactive=False, container=True
                )
                chatbot = gr.Chatbot(label="Conversation", height=400)
                user_input = gr.Textbox(
                    label="Your question", placeholder="Ask about the PDF and press Enter..."
                )
            with gr.Tab("Logs"):
                gr.Markdown(
                    """## Output Logs

                    This tab displays the detailed outputs returned by the model.
                    *Structured Logs* contains the parsed JSON objects for each
                    answer, while *Raw JSON Logs* shows the verbatim JSON
                    strings. Click **Refresh Logs** after asking questions
                    to update these views.
                    """
                )
                refresh_btn = gr.Button("Refresh Logs", variant="secondary")
                structured_log_json = gr.JSON(
                    label="Structured Logs", value=[]
                )
                raw_log_text = gr.Textbox(
                    label="Raw JSON Logs", value="", lines=10, interactive=False, container=True
                )
            with gr.Tab("Raw View"):
                gr.Markdown(
                    """## Raw View

                    This tab streams the raw JSON outputs from the model in real
                    time. Each response is appended to the view automatically
                    when you send a question in the Chat tab.
                    """
                )
                raw_view_box = gr.Textbox(
                    label="Raw JSON Stream", value="", lines=20, interactive=False, container=True
                )
        # Bind events outside the Tabs context so that all components are defined.
        upload_button.click(
            upload_and_prepare,
            inputs=[pdf_input, api_key_input],
            outputs=status_output,
        )
        user_input.submit(
            chat,
            inputs=[user_input, chatbot],
            outputs=[chatbot, user_input, raw_view_box],
        )
        refresh_btn.click(
            get_structured_logs,
            inputs=None,
            outputs=structured_log_json,
        )
        refresh_btn.click(
            get_raw_logs,
            inputs=None,
            outputs=raw_log_text,
        )
    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
