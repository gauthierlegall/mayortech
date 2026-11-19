"""Bounded, read-only MIME extraction. No URL fetch, rendering, or file write."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser


class MailParseError(ValueError):
    pass


@dataclass(frozen=True)
class MailAttachment:
    filename: str
    content_type: str
    content: bytes = field(repr=False)
    sha256: str
    inline: bool

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(frozen=True)
class ParsedMail:
    subject: str
    sender: str
    to: tuple[str, ...]
    received_at: datetime | None
    message_id: str | None
    thread_id: str | None
    text: str = field(repr=False)
    attachments: tuple[MailAttachment, ...]
    sha256: str
    text_sha256: str
    warnings: tuple[str, ...]


class _PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head", "template"}:
            self.hidden.append(tag)
        elif not self.hidden and tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        elif not self.hidden and tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _filename(value: str | None, ordinal: int) -> str:
    # Treat both POSIX and Windows separators as untrusted; never use as a path.
    leaf = (value or "").replace("\\", "/").split("/")[-1]
    leaf = "".join(char for char in leaf if char.isprintable() and char not in ":\x00")
    return leaf[:200] if leaf not in {"", ".", ".."} else f"attachment-{ordinal}"


def _decode_part(part: Message, warnings: list[str]) -> str:
    raw = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, errors="strict")
    except (UnicodeError, LookupError):
        warnings.append("body_encoding_replaced")
        return raw.decode("utf-8", errors="replace")


_MESSAGE_ID = re.compile(r"<[^<>\s@]{1,200}@[^<>\s@]{1,200}>")


def _thread_hint(message: Message, message_id: str | None, warnings: list[str]) -> str | None:
    """RFC header hint only, not proof of sender, authority or access rights."""
    for header in ("References", "In-Reply-To"):
        values = message.get_all(header, [])
        if not values:
            continue
        raw = str(values[0]).strip()
        identifiers = _MESSAGE_ID.findall(raw)
        remainder = _MESSAGE_ID.sub("", raw).strip()
        if len(values) != 1 or len(raw) > 8192 or not identifiers or len(identifiers) > 100 or remainder:
            warnings.append("malformed_thread_reference")
            return None  # Never use an invalid reference as an independent thread.
        if header == "In-Reply-To" and len(identifiers) != 1:
            warnings.append("ambiguous_thread_reference")
            return None
        return identifiers[0]
    return message_id


def parse_eml(raw: bytes, *, max_bytes: int = 10_000_000, max_parts: int = 100,
              max_attachment_bytes: int = 5_000_000, max_text_chars: int = 250_000,
              max_depth: int = 20) -> ParsedMail:
    """Extract immutable provenance. The caller retains the bounded original MIME.

    Date is the untrusted Date header, not a certified delivery timestamp. A missing
    timezone remains unknown; no implicit machine timezone is applied.
    """
    if not isinstance(raw, bytes) or not raw:
        raise MailParseError("mail_bytes_required")
    if len(raw) > max_bytes:
        raise MailParseError("mail_too_large")
    warnings: list[str] = []
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except (ValueError, RecursionError) as exc:
        raise MailParseError("invalid_mime") from exc
    attachments: list[MailAttachment] = []
    body_candidates: list[Message] = []
    total = 0
    count = 0
    stack = [(message, 0)]
    while stack:
        part, depth = stack.pop()
        count += 1
        if count > max_parts or depth > max_depth:
            raise MailParseError("mime_structure_limit")
        if part.defects:
            warnings.append("mime_defects")
        attachment = (part.get_content_disposition() == "attachment" or part.get_filename() is not None
                      or part.get_content_type() == "message/rfc822"
                      or (part.get_content_maintype() not in {"multipart", "text"}))
        if attachment:
            if part.get_content_type() == "message/rfc822":
                children = part.get_payload()
                content = b"\n".join(child.as_bytes(policy=policy.default) for child in children) if isinstance(children, list) else b""
            else:
                content = part.get_payload(decode=True) or b""
            total += len(content)
            if len(content) > max_attachment_bytes or total > max_bytes:
                raise MailParseError("attachment_too_large")
            attachments.append(MailAttachment(
                filename=_filename(part.get_filename(), len(attachments) + 1),
                content_type=part.get_content_type(), content=content,
                sha256=hashlib.sha256(content).hexdigest(), inline=part.get_content_disposition() == "inline",
            ))
            continue  # Never mix forwarded/attached mail content into the parent body.
        if part.is_multipart():
            stack.extend((child, depth + 1) for child in reversed(part.get_payload()))
        elif part.get_content_type() in {"text/plain", "text/html"}:
            body_candidates.append(part)
    # Prefer the primary plain alternative; quoted history remains source data.
    primary = message.get_body(preferencelist=("plain", "html"))
    if primary not in body_candidates:
        primary = next((part for part in body_candidates if part.get_content_type() == "text/plain"), None)
        primary = primary or (body_candidates[0] if body_candidates else None)
    text = _decode_part(primary, warnings) if primary is not None else ""
    if primary is not None and primary.get_content_type() == "text/html":
        parser = _PlainHTML()
        parser.feed(text)
        parser.close()
        text = re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
        warnings.append("html_converted_to_text")
    if len(text) > max_text_chars:
        raise MailParseError("body_too_large")
    date = None
    if message.get("Date"):
        try:
            date = parsedate_to_datetime(str(message["Date"]))
            if date.tzinfo is None or date.utcoffset() is None:
                date = None
                warnings.append("date_timezone_missing")
        except (TypeError, ValueError, OverflowError):
            warnings.append("invalid_date")
    else:
        warnings.append("missing_date")
    ids = message.get_all("Message-ID", [])
    message_id = str(ids[0]).strip() if len(ids) == 1 else None
    if not message_id:
        warnings.append("missing_message_id" if not ids else "multiple_message_ids")
    elif not _MESSAGE_ID.fullmatch(message_id):
        message_id = None
        warnings.append("invalid_message_id")
    thread_id = _thread_hint(message, message_id, warnings)
    from_addresses = getaddresses([str(value) for value in message.get_all("From", [])])
    sender = from_addresses[0][1] if len(from_addresses) == 1 else ""
    if not sender:
        warnings.append("sender_unknown")
    recipients = tuple(address for _, address in getaddresses([str(value) for value in message.get_all("To", [])]) if address)
    return ParsedMail(
        subject=str(message.get("Subject", "")), sender=sender, to=recipients,
        received_at=date, message_id=message_id, thread_id=thread_id, text=text, attachments=tuple(attachments),
        sha256=hashlib.sha256(raw).hexdigest(), text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        warnings=tuple(dict.fromkeys(warnings)),
    )
