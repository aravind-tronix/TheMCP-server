from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import decode_header
from base64 import urlsafe_b64decode
from email import message_from_bytes
import json
import asyncio
import smtplib
from .utils import get_gmail_service, get_user_email, handle_gmail_error, load_smtp_config, validate_pdf_attachment

mcp = FastMCP("GmailEmails")


class SendEmailArgs(BaseModel):
    recipient_id: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    message: str = Field(description="Email content text")
    attachment_path: Optional[str] = Field(
        default=None, description="Path to PDF attachment (optional)")


class ReadEmailArgs(BaseModel):
    email_id: str = Field(description="Email ID")


class TrashEmailArgs(BaseModel):
    email_id: str = Field(description="Email ID")


class MarkEmailAsReadArgs(BaseModel):
    email_id: str = Field(description="Email ID")


def decode_mime_header(header: str) -> str:
    """Decode encoded email headers."""
    decoded_parts = decode_header(header)
    decoded_string = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_string += part.decode(encoding or "utf-8")
        else:
            decoded_string += part
    return decoded_string


@mcp.tool()
async def send_email(args: Dict[str, Any]) -> str:
    """Send an email to a recipient using SMTP, with optional PDF attachment."""
    try:
        parsed = SendEmailArgs(**args)
        config = load_smtp_config()
        smtp_server = config["smtp_server"]
        smtp_port = config["smtp_port"]
        email = config["email"]
        app_password = config["app_password"]

        # Create MIME message
        msg = MIMEMultipart()
        msg["To"] = parsed.recipient_id
        msg["From"] = email
        msg["Subject"] = parsed.subject
        msg.attach(MIMEText(parsed.message, "plain"))

        # Add PDF attachment if provided
        if parsed.attachment_path:
            filename = validate_pdf_attachment(parsed.attachment_path)
            with open(parsed.attachment_path, "rb") as fp:
                att = MIMEApplication(fp.read(), _subtype="pdf")
                att.add_header("Content-Disposition",
                               "attachment", filename=filename)
                msg.attach(att)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)

        return json.dumps({"status": "success", "message": f"Email sent to {parsed.recipient_id}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_unread_emails(args: Dict[str, Any]) -> str:
    """Retrieve unread emails from the inbox."""
    try:
        service = get_gmail_service()
        query = "in:inbox is:unread category:primary"
        response = await asyncio.to_thread(
            service.users().messages().list(userId="me", q=query).execute
        )
        messages = response.get("messages", [])
        while "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = await asyncio.to_thread(
                service.users().messages().list(userId="me", q=query, pageToken=page_token).execute
            )
            messages.extend(response.get("messages", []))
        return json.dumps({"messages": [{"id": msg["id"]} for msg in messages]})
    except Exception as e:
        return json.dumps(handle_gmail_error(e))


@mcp.tool()
async def read_email(args: Dict[str, Any]) -> str:
    """Retrieve email contents including to, from, subject, and content."""
    try:
        parsed = ReadEmailArgs(**args)
        service = get_gmail_service()
        msg = await asyncio.to_thread(
            service.users().messages().get(userId="me", id=parsed.email_id, format="raw").execute
        )
        raw_data = msg["raw"]
        decoded_data = urlsafe_b64decode(raw_data)
        mime_message = message_from_bytes(decoded_data)
        body = None
        if mime_message.is_multipart():
            for part in mime_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = mime_message.get_payload(decode=True).decode()
        email_metadata = {
            "content": body,
            "subject": decode_mime_header(mime_message.get("subject", "")),
            "from": mime_message.get("from", ""),
            "to": mime_message.get("to", ""),
            "date": mime_message.get("date", "")
        }
        await asyncio.to_thread(
            service.users().messages().modify(userId="me", id=parsed.email_id,
                                              body={"removeLabelIds": ["UNREAD"]}).execute
        )
        return json.dumps(email_metadata)
    except Exception as e:
        return json.dumps(handle_gmail_error(e))


@mcp.tool()
async def trash_email(args: Dict[str, Any]) -> str:
    """Move an email to the trash."""
    try:
        parsed = TrashEmailArgs(**args)
        service = get_gmail_service()
        await asyncio.to_thread(
            service.users().messages().trash(userId="me", id=parsed.email_id).execute
        )
        return json.dumps({"message": f"Email {parsed.email_id} moved to trash"})
    except Exception as e:
        return json.dumps(handle_gmail_error(e))


@mcp.tool()
async def mark_email_as_read(args: Dict[str, Any]) -> str:
    """Mark an email as read."""
    try:
        parsed = MarkEmailAsReadArgs(**args)
        service = get_gmail_service()
        await asyncio.to_thread(
            service.users().messages().modify(userId="me", id=parsed.email_id,
                                              body={"removeLabelIds": ["UNREAD"]}).execute
        )
        return json.dumps({"message": f"Email {parsed.email_id} marked as read"})
    except Exception as e:
        return json.dumps(handle_gmail_error(e))
