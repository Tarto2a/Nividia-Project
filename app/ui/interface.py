import os
import tempfile
from pathlib import Path
from typing import Any, List, Dict, Optional

import gradio as gr
import httpx

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CUSTOM_CSS = """
:root{
    --bg:#0d1117;
    --panel:#151b23;
    --panel-2:#1b2330;
    --border:#303947;
    --text:#edf2f7;
    --muted:#9aa8b8;
    --accent:#19c37d;
    --accent-2:#4cc9f0;
    --danger:#ef4444;
}
body,
.gradio-container{
    background:
        radial-gradient(circle at 18% 0%,rgba(25,195,125,0.12),transparent 28%),
        radial-gradient(circle at 80% 8%,rgba(76,201,240,0.10),transparent 30%),
        var(--bg) !important;
    color:var(--text);
    font-family:Inter,ui-sans-serif,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
}
.app-shell{
    max-width:1440px;
    margin:0 auto;
    padding:18px;
}
.topbar{
    align-items:center;
    background:rgba(21,27,35,0.82);
    border:1px solid var(--border);
    border-radius:8px;
    box-shadow:0 18px 42px rgba(0,0,0,0.24);
    margin-bottom:14px;
    padding:14px 16px;
}
.brand-title h2{
    font-size:1.35rem;
    line-height:1.2;
    margin:0 0 4px;
}
.brand-title p{
    color:var(--muted);
    margin:0;
}
.panel{
    background:rgba(21,27,35,0.88);
    border:1px solid var(--border);
    border-radius:8px;
    box-shadow:0 12px 28px rgba(0,0,0,0.20);
    padding:14px;
}
.rail{
    min-width:220px;
}
.section-title h3{
    font-size:0.95rem;
    letter-spacing:0;
    margin:0 0 8px;
}
.hint,
.hint p{
    color:var(--muted);
    font-size:0.88rem;
    line-height:1.45;
    margin:0;
}
.status-card textarea,
.status-card input{
    font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
    font-size:0.82rem !important;
}
.workspace{
    gap:14px;
}
.doc-heading{
    background:rgba(21,27,35,0.88);
    border:1px solid var(--border);
    border-radius:8px;
    padding:10px 12px;
}
.doc-heading h3{
    margin:0;
}
.chat-panel{
    padding:0;
}
.chat-panel .wrap{
    border-radius:8px !important;
}
.composer{
    align-items:stretch;
    background:rgba(21,27,35,0.88);
    border:1px solid var(--border);
    border-radius:8px;
    padding:10px;
}
.actions-row{
    display:flex;
    flex-wrap:wrap;
    gap:8px;
}
.quick-btn button,
.primary-btn button,
.secondary-btn button{
    border-radius:7px !important;
    font-weight:650 !important;
}
.primary-btn button{
    background:var(--accent) !important;
    border-color:var(--accent) !important;
    color:#06120c !important;
}
.quick-btn button{
    min-width:150px;
}
.dataframe-wrap,
.preview-wrap{
    overflow:hidden;
}
.preview-wrap img{
    border-radius:6px;
    object-fit:contain;
}
footer{display:none !important}
@media (max-width: 900px){
    .app-shell{padding:10px}
    .rail{min-width:0}
    .quick-btn button{min-width:100%}
}
"""


def _format_citations(citations: List[dict]) -> str:
    if not citations:
        return ""
    lines = ["Sources:"]
    for item in citations:
        source = item.get("source", "unknown")
        section = item.get("section", "N/A")
        lines.append(f"- {source} ({section})")
    return "\n".join(lines)


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        return response.json().get("detail", response.text)
    except Exception:
        return response.text


def _welcome_message(has_docs: bool = False) -> List[dict[str, str]]:
    if has_docs:
        text = (
            "Your documents are ready. Ask a question or use one of the quick actions below.\n\n"
            "Tip: Ask specific questions like 'What are late payment penalties?' for better answers."
        )
    else:
        text = (
            "Welcome. Start by uploading one or more contract files on the right panel.\n\n"
            "After upload, you can ask questions, request a summary, or check specific risk clauses."
        )
    return [{"role": "assistant", "content": text}]


def _files_table(file_names: List[str]) -> List[List[str]]:
    return [[name] for name in file_names]


def _generate_pdf_preview(pdf_path: str) -> Optional[str]:
    """Render the first page of a PDF to a PNG and return the temp path."""
    if not fitz:
        return None
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        pix.save(tmp.name)
        doc.close()
        return tmp.name
    except Exception:
        return None


def select_document(selected: str, session: dict | None):
    """Update the UI to show the selected document and a preview if available."""
    if not selected:
        return (
            gr.update(value="### No document selected"),
            gr.update(value=None),
            gr.update(value=None),
            "No document selected.",
        )

    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    candidate = upload_dir / selected
    title_html = f"### {selected} <span style='background:#16a34a;color:white;padding:4px 8px;border-radius:6px;font-size:0.8rem;'>Processed</span>"
    preview_img = None
    preview_file_value = None
    if candidate.exists():
        preview_file_value = str(candidate)
        if candidate.suffix.lower() == ".pdf":
            preview_img = _generate_pdf_preview(str(candidate))

    status_text = "Document selected." if preview_file_value else "Document selected (preview unavailable)."
    return (
        gr.update(value=title_html),
        gr.update(value=preview_img),
        gr.update(value=preview_file_value),
        status_text,
    )


def check_api_health() -> str:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return f"API status: Offline\nDetails: {exc}"

    readiness = "Ready" if data.get("services_ready") else "Running (documents not initialized yet)"
    return f"API status: Online\nService state: {readiness}"


def upload_files(files: List[gr.File], session: dict | None):
    session = session or {"has_docs": False, "files": []}
    if not files:
        return (
            "Please upload at least one .pdf or .docx file.",
            session,
            _files_table(session.get("files", [])),
            "Step 1 of 2: Upload a contract file to begin.",
            _welcome_message(session.get("has_docs", False)),
            _welcome_message(session.get("has_docs", False)),
            "No files uploaded yet.",
            gr.update(choices=session.get("files", []), value=None),
            gr.update(value="### No document selected"),
            gr.update(value=None),
            gr.update(value=None),
        )

    prepared = []
    for f in files:
        file_path = Path(f.name)
        prepared.append(("files", (file_path.name, open(file_path, "rb"), "application/octet-stream")))

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{API_BASE_URL}/upload", files=prepared)
            response.raise_for_status()
            data = response.json()
            uploaded_files = data.get("files", [])
            session = {"has_docs": True, "files": uploaded_files}
            # prepare document selector + preview for first uploaded file
            selected = uploaded_files[0] if uploaded_files else None
            upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
            preview_img = None
            preview_file_value = None
            title_html = "### No document selected"
            if selected:
                candidate = upload_dir / selected
                title_html = f"### {selected} <span style='background:#16a34a;color:white;padding:4px 8px;border-radius:6px;font-size:0.8rem;'>Processed</span>"
                if candidate.exists() and candidate.suffix.lower() == ".pdf":
                    preview_img = _generate_pdf_preview(str(candidate))
                    preview_file_value = str(candidate)

            return (
                f"{data.get('message')}\nFiles: {', '.join(uploaded_files)}",
                session,
                _files_table(uploaded_files),
                "Step 2 of 2: Ask a question in chat. You can also click 'Summarize Contract'.",
                _welcome_message(True),
                _welcome_message(True),
                "Documents indexed successfully. You are ready to chat.",
                gr.update(choices=uploaded_files, value=selected),
                gr.update(value=title_html),
                gr.update(value=preview_img),
                gr.update(value=preview_file_value),
            )
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text
        suffix = f" - {detail}" if detail else ""
        return (
            f"Upload failed ({exc.response.status_code} {exc.response.reason_phrase}){suffix}",
            session,
            _files_table(session.get("files", [])),
            "Upload failed. Please verify file type/contents and try again.",
            _welcome_message(session.get("has_docs", False)),
            _welcome_message(session.get("has_docs", False)),
            "Upload failed. The assistant is not ready yet.",
            gr.update(choices=session.get("files", []), value=None),
            gr.update(value="### No document selected"),
            gr.update(value=None),
            gr.update(value=None),
        )
    except Exception as exc:
        return (
            f"Upload failed: {exc}",
            session,
            _files_table(session.get("files", [])),
            "Upload failed due to a local/network issue. Retry after checking API health.",
            _welcome_message(session.get("has_docs", False)),
            _welcome_message(session.get("has_docs", False)),
            "Upload failed. The assistant is not ready yet.",
            gr.update(choices=session.get("files", []), value=None),
            gr.update(value="### No document selected"),
            gr.update(value=None),
            gr.update(value=None),
        )
    finally:
        for _, (_, file_obj, _) in prepared:
            try:
                file_obj.close()
            except Exception:
                pass


def ask_question(message: str, history: List[dict[str, Any]], session: dict | None):
    history = history or _welcome_message((session or {}).get("has_docs", False))
    message = (message or "").strip()
    if not message:
        return history, history, "", "Type a question to continue."
    if not (session or {}).get("has_docs"):
        history.append({"role": "user", "content": message})
        history.append(
            {
                "role": "assistant",
                "content": (
                    "I don't have any indexed contract yet. "
                    "Please upload a PDF or DOCX file first from the right panel."
                ),
            }
        )
        return history, history, "", "Upload at least one document before asking questions."
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{API_BASE_URL}/ask", json={"question": message})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = _extract_error_detail(exc.response)
        assistant_reply = (
            f"Request failed ({exc.response.status_code} {exc.response.reason_phrase}): {detail}"
        )
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": assistant_reply})
        return history, history, "", "Question request failed. Check API health and try again."
    except Exception as exc:
        assistant_reply = f"Request failed: {exc}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": assistant_reply})
        return history, history, "", "Question request failed. Check connection and retry."

    answer = data.get("answer", "")
    citations = _format_citations(data.get("citations", []))
    full_answer = answer if not citations else f"{answer}\n\n{citations}"

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": full_answer})
    return history, history, "", "Answer generated successfully."


def summarize_contract(history: List[dict[str, Any]], session: dict | None):
    history = history or _welcome_message((session or {}).get("has_docs", False))
    prompt = "Summarize the uploaded contract"
    if not (session or {}).get("has_docs"):
        history.append({"role": "user", "content": prompt})
        history.append(
            {
                "role": "assistant",
                "content": "Please upload a contract first, then I can provide an executive summary.",
            }
        )
        return history, history, "Upload a contract first to use summarize."
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{API_BASE_URL}/summary")
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = _extract_error_detail(exc.response)
        assistant_reply = (
            f"Summary failed ({exc.response.status_code} {exc.response.reason_phrase}): {detail}"
        )
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": assistant_reply})
        return history, history, "Summary failed. Check API health and retry."
    except Exception as exc:
        assistant_reply = f"Summary failed: {exc}"
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": assistant_reply})
        return history, history, "Summary failed due to connection/runtime issue."

    answer = data.get("answer", "")
    citations = _format_citations(data.get("citations", []))
    full_answer = answer if not citations else f"{answer}\n\n{citations}"
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": full_answer})
    return history, history, "Summary generated successfully."


def clear_conversation(session: dict | None):
    has_docs = (session or {}).get("has_docs", False)
    fresh = _welcome_message(has_docs)
    status_text = "Chat cleared. Documents are still indexed and ready." if has_docs else "Chat cleared."
    return fresh, fresh, status_text


def use_quick_prompt(prompt: str, history: List[dict[str, Any]], session: dict | None):
    return ask_question(prompt, history, session)


def quick_payment_terms(history: List[dict[str, Any]], session: dict | None):
    return use_quick_prompt("Summarize the payment terms and due dates.", history, session)


def quick_termination(history: List[dict[str, Any]], session: dict | None):
    return use_quick_prompt("Explain the termination clause and notice periods.", history, session)


def quick_risks(history: List[dict[str, Any]], session: dict | None):
    return use_quick_prompt("Identify potentially risky or one-sided clauses.", history, session)


def download_summary(session: dict | None):
    if not (session or {}).get("has_docs"):
        return "No indexed documents to summarize.", None
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{API_BASE_URL}/summary")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = _extract_error_detail(exc.response)
        return f"Summary failed ({exc.response.status_code}): {detail}", None
    except Exception as exc:
        return f"Summary failed: {exc}", None

    answer = data.get("answer", "")
    citations = _format_citations(data.get("citations", []))
    full_answer = answer if not citations else f"{answer}\n\n{citations}"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp.write(full_answer.encode("utf-8"))
    tmp.flush()
    tmp.close()
    return "Summary ready for download.", tmp.name


def export_chat(history: List[dict[str, Any]]):
    if not history:
        return "No conversation to export.", None
    lines = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        lines.append(f"{role.upper()}:\n{content}\n\n")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp.write("\n".join(lines).encode("utf-8"))
    tmp.flush()
    tmp.close()
    return "Chat exported.", tmp.name


with gr.Blocks(title="Smart Contract Assistant", fill_width=True) as demo:
    with gr.Column(elem_classes=["app-shell"]):
        with gr.Row(elem_classes=["topbar"]):
            with gr.Column(scale=8, elem_classes=["brand-title"]):
                gr.Markdown(
                    """
## Smart Contract Assistant
Upload agreements, ask direct questions, and get citation-backed answers.
"""
                )
            with gr.Column(scale=4, elem_classes=["status-card"]):
                with gr.Row():
                    health_button = gr.Button("Check API Health", elem_classes=["secondary-btn"])
                    health_status = gr.Textbox(
                        label="API Health",
                        value="API status: Not checked",
                        interactive=False,
                        lines=2,
                    )

        memory_state = gr.State(_welcome_message(False))
        session_state = gr.State({"has_docs": False, "files": []})

        with gr.Row(elem_classes=["workspace"]):
            with gr.Column(scale=2, elem_classes=["panel", "rail"]):
                gr.Markdown("### Workspace", elem_classes=["section-title"])
                gr.Markdown(
                    "Select an indexed document to preview it, then use the chat to inspect clauses.",
                    elem_classes=["hint"],
                )
                document_selector = gr.Dropdown(
                    choices=[],
                    label="Indexed Documents",
                    value=None,
                    interactive=True,
                )
                assistant_status = gr.Textbox(
                    label="Assistant Status",
                    value="No files uploaded yet.",
                    interactive=False,
                    lines=4,
                )
                gr.Markdown("### Session", elem_classes=["section-title"])
                clear_button = gr.Button("Clear Chat", elem_classes=["secondary-btn"])
                export_button = gr.Button("Export Chat", elem_classes=["secondary-btn"])
                export_file = gr.File(visible=False)
                gr.Markdown("Ahmed Tarek", elem_classes=["hint"])

            with gr.Column(scale=6):
                doc_title = gr.Markdown("### No document selected", elem_classes=["doc-heading"])
                with gr.Row(elem_classes=["chat-panel"]):
                    chatbot = gr.Chatbot(
                        value=_welcome_message(False),
                        height=560,
                        label="Contract Chat",
                    )
                with gr.Row(elem_classes=["composer"]):
                    user_message = gr.Textbox(
                        show_label=False,
                        placeholder="Ask about payment terms, termination, obligations, risks...",
                        lines=2,
                        scale=8,
                    )
                    send_btn = gr.Button("Send", scale=1, elem_classes=["primary-btn"])
                with gr.Row(elem_classes=["actions-row"]):
                    quick_btn_1 = gr.Button("Payment Terms", elem_classes=["quick-btn"])
                    quick_btn_2 = gr.Button("Termination Clause", elem_classes=["quick-btn"])
                    quick_btn_3 = gr.Button("Risky Clauses", elem_classes=["quick-btn"])
                with gr.Row():
                    summary_button = gr.Button("Summarize Contract", elem_classes=["primary-btn"])
                    summary_download_button = gr.Button(
                        "Download Latest Summary",
                        elem_classes=["secondary-btn"],
                    )
                    summary_file = gr.File(visible=False)

            with gr.Column(scale=4):
                with gr.Column(elem_classes=["panel"]):
                    gr.Markdown("### Upload Documents", elem_classes=["section-title"])
                    gr.Markdown(
                        "Drag and drop PDF or DOCX files, then index them for chat.",
                        elem_classes=["hint"],
                    )
                    uploader = gr.File(
                        label="PDF or DOCX files",
                        file_count="multiple",
                        file_types=[".pdf", ".docx"],
                    )
                    upload_button = gr.Button("Upload and Index", elem_classes=["primary-btn"])
                    upload_status = gr.Textbox(label="Upload Status", interactive=False, lines=3)

                with gr.Column(elem_classes=["panel", "dataframe-wrap"]):
                    gr.Markdown("### Current Contract Set", elem_classes=["section-title"])
                    indexed_files = gr.Dataframe(
                        headers=["Indexed files"],
                        datatype=["str"],
                        value=[],
                        interactive=False,
                        row_count=(4, "dynamic"),
                    )

                with gr.Column(elem_classes=["panel", "preview-wrap"]):
                    gr.Markdown("### Document Preview", elem_classes=["section-title"])
                    doc_preview = gr.Image(
                        value=None,
                        label="First page preview",
                        height=360,
                    )
                    preview_file = gr.File(visible=False)

    # Wire up interactions
    upload_button.click(
        upload_files,
        inputs=[uploader, session_state],
        outputs=[
            upload_status,
            session_state,
            indexed_files,
            memory_state,
            chatbot,
            memory_state,
            assistant_status,
            document_selector,
            doc_title,
            doc_preview,
            preview_file,
        ],
    )

    # Update preview when a document is selected from the sidebar
    document_selector.change(
        select_document,
        inputs=[document_selector, session_state],
        outputs=[doc_title, doc_preview, preview_file, assistant_status],
    )

    health_button.click(check_api_health, outputs=[health_status])
    send_btn.click(ask_question, inputs=[user_message, memory_state, session_state], outputs=[chatbot, memory_state, user_message, assistant_status])
    summary_button.click(summarize_contract, inputs=[memory_state, session_state], outputs=[chatbot, memory_state, assistant_status])
    clear_button.click(clear_conversation, inputs=[session_state], outputs=[chatbot, memory_state, assistant_status])
    quick_btn_1.click(quick_payment_terms, inputs=[memory_state, session_state], outputs=[chatbot, memory_state, user_message, assistant_status])
    quick_btn_2.click(quick_termination, inputs=[memory_state, session_state], outputs=[chatbot, memory_state, user_message, assistant_status])
    quick_btn_3.click(quick_risks, inputs=[memory_state, session_state], outputs=[chatbot, memory_state, user_message, assistant_status])

    summary_download_button.click(download_summary, inputs=[session_state], outputs=[assistant_status, summary_file])
    export_button.click(export_chat, inputs=[memory_state], outputs=[assistant_status, export_file])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, css=CUSTOM_CSS)
