"""
Google Drive Knowledge Loader

Indexes documents from one or more Google Drive folders into the knowledge base.
Supports: Google Docs, PDF, DOCX, Google Slides, plain text.
Skips video files (MP4, MOV) — stores only metadata/title for those.

Folder structure recommended on your Drive:
  📁 SBITIS Knowledge Base/
    📁 SOPs/                    ← Standard Operating Procedures
    📁 Sales Frameworks/        ← Scripts, objection handling, frameworks
    📁 Training Docs/           ← Onboarding materials, guides
    📁 Onboarding Videos/       ← MP4/MOV — titles + descriptions indexed only
    📁 Ad Copy & Scripts/       ← Meta ad copy, video scripts
    📁 WhatsApp Sequences/      ← Follow-up message sequences
"""

import io
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import config

log = structlog.get_logger(__name__)

# MIME types we can extract text from
_TEXT_MIME_TYPES = {
    "application/vnd.google-apps.document",           # Google Docs
    "application/vnd.google-apps.presentation",       # Google Slides
    "application/pdf",                                # PDF
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "text/plain",
    "text/markdown",
}

# Video types — index title + description only
_VIDEO_MIME_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "application/vnd.google-apps.video",
}

# Folder category tags (matched against folder name)
_CATEGORY_HINTS = {
    "sop": "SOP",
    "standard operating": "SOP",
    "sales framework": "sales_framework",
    "script": "sales_framework",
    "objection": "sales_framework",
    "training": "training",
    "onboarding": "onboarding",
    "video": "video",
    "ad copy": "ad_copy",
    "whatsapp": "whatsapp_sequence",
    "sequence": "whatsapp_sequence",
    "content": "content_strategy",
}


@dataclass
class KnowledgeDocument:
    """A single document extracted from Drive."""
    doc_id: str                          # Google Drive file ID
    title: str
    category: str                        # sop | sales_framework | training | video | etc.
    folder_path: str                     # e.g. "SOPs/Closing Process"
    content: str                         # Full text content (empty for videos)
    is_video: bool = False
    video_url: str = ""                  # Drive URL for videos
    mime_type: str = ""
    last_modified: str = ""
    metadata: dict = field(default_factory=dict)

    def to_metadata(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "category": self.category,
            "folder_path": self.folder_path,
            "is_video": self.is_video,
            "video_url": self.video_url,
            "mime_type": self.mime_type,
            "last_modified": self.last_modified,
            **self.metadata,
        }


def _infer_category(folder_path: str, title: str) -> str:
    """Infer document category from folder path and title."""
    combined = (folder_path + " " + title).lower()
    for hint, category in _CATEGORY_HINTS.items():
        if hint in combined:
            return category
    return "general"


class DriveKnowledgeLoader:
    """
    Loads and extracts text from Google Drive folders.
    Pass a list of folder IDs from your Drive URLs.
    """

    def __init__(
        self,
        service_account_json: str = config.GOOGLE_SERVICE_ACCOUNT_JSON,
        folder_ids: list[str] | None = None,
    ):
        self.service_account_json = service_account_json
        # folder_ids from config + any passed directly
        self.folder_ids = folder_ids or config.KNOWLEDGE_BASE_FOLDER_IDS
        self._drive_service = None
        self._docs_service = None

    def _get_services(self):
        if self._drive_service is None:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            scopes = [
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/documents.readonly",
            ]
            creds = Credentials.from_service_account_file(
                self.service_account_json, scopes=scopes
            )
            self._drive_service = build("drive", "v3", credentials=creds)
            self._docs_service = build("docs", "v1", credentials=creds)
        return self._drive_service, self._docs_service

    def load_all(self, changed_since: datetime | None = None) -> list[KnowledgeDocument]:
        """
        Load all documents from all configured Drive folders.
        If changed_since is set, only loads files modified after that datetime.
        """
        all_docs: list[KnowledgeDocument] = []

        for folder_id in self.folder_ids:
            try:
                docs = self._load_folder(folder_id, parent_path="", changed_since=changed_since)
                all_docs.extend(docs)
                log.info("drive_loader.folder_done", folder_id=folder_id, docs=len(docs))
            except Exception as e:
                log.error("drive_loader.folder_failed", folder_id=folder_id, error=str(e))

        log.info("drive_loader.load_all_done", total=len(all_docs))
        return all_docs

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
    def _list_files_in_folder(self, folder_id: str) -> list[dict]:
        """List all files and subfolders in a Drive folder."""
        drive, _ = self._get_services()
        results = []
        page_token = None

        while True:
            response = drive.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink, description)",
                pageToken=page_token,
                pageSize=100,
            ).execute()

            results.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def _load_folder(
        self,
        folder_id: str,
        parent_path: str,
        changed_since: datetime | None,
    ) -> list[KnowledgeDocument]:
        """Recursively load a folder and all subfolders."""
        docs: list[KnowledgeDocument] = []
        files = self._list_files_in_folder(folder_id)

        for f in files:
            mime = f.get("mimeType", "")
            name = f.get("name", "")
            file_id = f["id"]
            modified = f.get("modifiedTime", "")
            folder_path = f"{parent_path}/{name}".strip("/")

            # Filter by modification date if requested
            if changed_since and modified:
                try:
                    mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    if mod_dt.replace(tzinfo=None) < changed_since.replace(tzinfo=None):
                        continue
                except Exception:
                    pass

            # Recurse into subfolders
            if mime == "application/vnd.google-apps.folder":
                sub_docs = self._load_folder(file_id, folder_path, changed_since)
                docs.extend(sub_docs)
                continue

            # Video files — index title and description only
            if mime in _VIDEO_MIME_TYPES:
                docs.append(
                    KnowledgeDocument(
                        doc_id=file_id,
                        title=name,
                        category=_infer_category(folder_path, name),
                        folder_path=folder_path,
                        content=f"[VIDEO] {name}\n{f.get('description', '')}",
                        is_video=True,
                        video_url=f.get("webViewLink", ""),
                        mime_type=mime,
                        last_modified=modified,
                    )
                )
                log.info("drive_loader.video_indexed", title=name)
                continue

            # Text-extractable files
            if mime in _TEXT_MIME_TYPES:
                try:
                    content = self._extract_text(file_id, mime)
                    if not content.strip():
                        log.warning("drive_loader.empty_content", title=name)
                        continue

                    docs.append(
                        KnowledgeDocument(
                            doc_id=file_id,
                            title=name,
                            category=_infer_category(folder_path, name),
                            folder_path=folder_path,
                            content=content,
                            mime_type=mime,
                            last_modified=modified,
                        )
                    )
                    log.info("drive_loader.doc_loaded", title=name, chars=len(content))
                except Exception as e:
                    log.error("drive_loader.extract_failed", title=name, error=str(e))

        return docs

    def _extract_text(self, file_id: str, mime_type: str) -> str:
        """Extract plain text from a Drive file based on its MIME type."""
        drive, docs_svc = self._get_services()

        # Google Docs → use Docs API for clean text
        if mime_type == "application/vnd.google-apps.document":
            return self._extract_google_doc(file_id, docs_svc)

        # Google Slides → export as plain text
        if mime_type == "application/vnd.google-apps.presentation":
            return self._export_as_text(file_id, drive, "text/plain")

        # PDF → export as plain text via Drive export
        if mime_type == "application/pdf":
            return self._extract_pdf(file_id, drive)

        # DOCX → export as plain text
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._export_as_text(file_id, drive, "text/plain")

        # Plain text / markdown — direct download
        return self._export_as_text(file_id, drive, "text/plain")

    def _extract_google_doc(self, file_id: str, docs_svc) -> str:
        """Extract structured text from a Google Doc."""
        doc = docs_svc.documents().get(documentId=file_id).execute()
        lines = []
        for element in doc.get("body", {}).get("content", []):
            paragraph = element.get("paragraph")
            if not paragraph:
                continue
            style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
            text_parts = []
            for run in paragraph.get("elements", []):
                t = run.get("textRun", {}).get("content", "")
                if t:
                    text_parts.append(t)
            line = "".join(text_parts).rstrip("\n")
            if line.strip():
                # Add markdown-style headers for structure
                if "HEADING_1" in style:
                    lines.append(f"\n# {line}")
                elif "HEADING_2" in style:
                    lines.append(f"\n## {line}")
                elif "HEADING_3" in style:
                    lines.append(f"\n### {line}")
                else:
                    lines.append(line)
        return "\n".join(lines)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def _export_as_text(self, file_id: str, drive, export_mime: str) -> str:
        """Export a Drive file as the given MIME type and return text."""
        response = drive.files().export(fileId=file_id, mimeType=export_mime).execute()
        if isinstance(response, bytes):
            return response.decode("utf-8", errors="replace")
        return str(response)

    def _extract_pdf(self, file_id: str, drive) -> str:
        """Download PDF and extract text using pdfminer."""
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
            import tempfile

            # Download PDF bytes
            request = drive.files().get_media(fileId=file_id)
            from googleapiclient.http import MediaIoBaseDownload

            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            buf.seek(0)

            # Extract text
            out = io.StringIO()
            extract_text_to_fp(buf, out, laparams=LAParams())
            return out.getvalue()

        except ImportError:
            # Fallback: try Drive's plain text export (works for many PDFs)
            try:
                return self._export_as_text(file_id, drive, "text/plain")
            except Exception:
                return "[PDF content could not be extracted — install pdfminer.six]"
