import os
import base64
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from src.core.interfaces import IEmailProvider
from src.models import EmailMessage

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailProvider(IEmailProvider):
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.creds = None
        self.service = None
        self.download_folder = "download"
        
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if os.path.exists(credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    with open(token_path, 'w') as token:
                        token.write(self.creds.to_json())
                else:
                    print("Warning: credentials.json not found. Gmail will not work.")
                    return

        self.service = build('gmail', 'v1', credentials=self.creds)

    def fetch_unread_emails(self, limit: int = 5) -> List[EmailMessage]:
        if not self.service: return []
        
        # Get unread messages
        results = self.service.users().messages().list(
            userId='me', q='is:unread', maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        email_objects = []

        for msg in messages:
            msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_detail['payload']
            headers = payload['headers']
            
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            thread_id = msg_detail['threadId']
            
            body = msg_detail.get('snippet', '')

            attachments = []
            parts = payload.get('parts', [])
            
            if not parts and 'body' in payload:
                pass 
            else:
                for part in parts:
                    filename = part.get('filename')
                    if not filename: continue
                    
                    # --- CRITICAL FIX: ALLOW ZIP FILES ---
                    # We now download .pdf AND .zip files
                    ext = filename.lower()
                    if ext.endswith('.pdf') or ext.endswith('.zip'):
                        if 'data' in part['body']:
                            data = part['body']['data']
                        elif 'attachmentId' in part['body']:
                            att_id = part['body']['attachmentId']
                            att = self.service.users().messages().attachments().get(
                                userId='me', messageId=msg['id'], id=att_id
                            ).execute()
                            data = att['data']
                        else:
                            continue
                        
                        file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                        path = os.path.join(self.download_folder, filename)
                        with open(path, 'wb') as f:
                            f.write(file_data)
                        attachments.append(path)
            
            email_objects.append(EmailMessage(
                id=msg['id'],
                thread_id=thread_id,
                sender=sender,
                subject=subject,
                body=body,
                attachments=attachments
            ))
        
        return email_objects

    def _create_message(self, to_email, subject, body_html, thread_id=None):
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        
        msg = MIMEText(body_html, 'html')
        message.attach(msg)
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}
        if thread_id:
            body['threadId'] = thread_id
        return body

    def send_reply(self, thread_id: str, to_email: str, body: str):
        if not self.service: return
        html_body = f"<p>{body.replace(chr(10), '<br>')}</p>"
        create_message = self._create_message(to_email, "Re: Invoice Reconciliation", html_body, thread_id)
        
        try:
            self.service.users().messages().send(userId="me", body=create_message).execute()
            print(f"Reply sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_new_email(self, to_email: str, subject: str, body: str) -> str:
        if not self.service: return None
        create_message = self._create_message(to_email, subject, body)
        try:
            sent_message = self.service.users().messages().send(userId="me", body=create_message).execute()
            print(f"Kickoff email sent to {to_email} (Thread: {sent_message['threadId']})")
            return sent_message['threadId']
        except Exception as e:
            print(f"Failed to send kickoff email: {e}")
            return None