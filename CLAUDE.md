# ChatPDF AI - Intelligent PDF Document Assistant

## Project Overview
An AI-powered application that allows users to upload PDF documents and have natural conversations about the content using Google Gemini AI. Users can ask questions, get summaries, extract information, and analyze documents through an intuitive chat interface.

**Target Market**: Students, researchers, professionals, legal firms, businesses with document-heavy workflows  
**Revenue Model**: $19-99/month per user (freemium model)  
**Value Proposition**: Save hours reading documents - chat with them instead

## Tech Stack
- **Backend**: Django 5.0 + Django REST Framework + PostgreSQL/SQLite
- **Frontend**: React 18 + Vite + Tailwind CSS
- **AI**: Google Gemini 1.5 Pro (supports 1M+ token context window)
- **PDF Processing**: PyPDF2 for text extraction
- **File Storage**: Django media files (local storage for dev)
- **Authentication**: dj-rest-auth (token-based)

## Core Features

### 1. PDF Upload & Processing
- Drag-and-drop or click-to-upload interface
- Support for multi-page PDFs (up to 100 pages/10MB)
- Extract text from PDF using PyPDF2
- Store extracted text in database
- Generate document summary automatically
- Display PDF preview with page navigation

### 2. Intelligent Chat Interface
- Natural language question answering about PDF content
- Context-aware responses using Gemini 1.5 Pro
- Conversation history per document
- Suggested questions to help users get started
- Citation references (page numbers where info was found)

### 3. Document Management
- List all uploaded documents
- Search documents by name or content
- Delete documents
- View document metadata (pages, size, upload date)
- Document categories/tags

### 4. AI Capabilities
- Answer questions about document content
- Summarize entire documents or specific sections
- Extract key information (dates, names, figures)
- Compare information across multiple documents
- Translate content to different languages

## Database Models

### Document Model
- `id` - Primary key (AutoField)
- `user` - Owner (ForeignKey to User)
- `title` - Document name (CharField, max_length=255)
- `file` - PDF file (FileField, upload_to='documents/')
- `extracted_text` - Full text content (TextField)
- `page_count` - Number of pages (IntegerField)
- `file_size` - File size in bytes (IntegerField)
- `summary` - AI-generated summary (TextField)
- `language` - Detected language (CharField, max_length=10)
- `uploaded_at` - Upload timestamp (DateTimeField, auto_now_add=True)

### Conversation Model
- `id` - Primary key (AutoField)
- `document` - Related document (ForeignKey to Document)
- `conversation_id` - Unique ID (UUIDField)
- `created_at` - Timestamp (DateTimeField, auto_now_add=True)

### Message Model
- `id` - Primary key (AutoField)
- `conversation` - Related conversation (ForeignKey to Conversation)
- `sender_type` - Who sent (choices: 'user'/'ai')
- `content` - Message text (TextField)
- `page_references` - Pages mentioned (JSONField, nullable)
- `timestamp` - When sent (DateTimeField, auto_now_add=True)

## API Endpoints

### Authentication
- `POST /api/auth/registration/` - Register new user
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/user/` - Current user

### Documents
- `GET /api/documents/` - List user's documents
- `POST /api/documents/upload/` - Upload PDF (multipart/form-data)
- `GET /api/documents/{id}/` - Document details
- `DELETE /api/documents/{id}/` - Delete document
- `GET /api/documents/{id}/preview/` - Get PDF preview data
- `GET /api/documents/{id}/summary/` - Get AI summary

### Chat
- `POST /api/chat/start/` - Start conversation with document
  - Input: document_id
  - Output: conversation_id
- `POST /api/chat/message/` - Send message
  - Input: conversation_id, message
  - Output: ai_response, page_references
- `GET /api/chat/history/{conversation_id}/` - Get chat history
- `GET /api/chat/suggestions/{document_id}/` - Get suggested questions

## AI Integration (Google Gemini)

### Gemini Setup
import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

text

### Chat Processing Flow
1. User uploads PDF → Extract text with PyPDF2
2. Generate document summary using Gemini
3. User asks question → Send to Gemini with document context
4. Gemini analyzes full document text (1M+ token context)
5. Return answer with page references
6. Store conversation history

### Prompt Template
You are an intelligent document assistant. You have access to the full content of this document:

DOCUMENT TITLE: {document_title}
DOCUMENT CONTENT:
{full_document_text}

CONVERSATION HISTORY:
{previous_messages}

USER QUESTION: {user_question}

Provide a detailed, accurate answer based ONLY on the document content. If the information is not in the document, say so clearly. Include page references where the information was found (if possible from page markers in text).

Answer:

text

## Frontend Structure

chatpdf-frontend/
├── src/
│ ├── components/
│ │ ├── auth/
│ │ │ ├── LoginForm.jsx
│ │ │ └── RegisterForm.jsx
│ │ ├── documents/
│ │ │ ├── DocumentUploader.jsx
│ │ │ ├── DocumentList.jsx
│ │ │ ├── DocumentCard.jsx
│ │ │ └── PDFViewer.jsx
│ │ ├── chat/
│ │ │ ├── ChatInterface.jsx
│ │ │ ├── MessageBubble.jsx
│ │ │ ├── SuggestedQuestions.jsx
│ │ │ └── TypingIndicator.jsx
│ │ └── common/
│ │ ├── Navbar.jsx
│ │ ├── Sidebar.jsx
│ │ └── LoadingSpinner.jsx
│ ├── services/
│ │ ├── api.js
│ │ ├── authService.js
│ │ ├── documentService.js
│ │ └── chatService.js
│ ├── context/
│ │ └── AuthContext.jsx
│ ├── pages/
│ │ ├── Login.jsx
│ │ ├── Register.jsx
│ │ ├── Dashboard.jsx
│ │ ├── DocumentView.jsx
│ │ └── ChatPage.jsx
│ ├── App.jsx
│ └── main.jsx
└── package.json

text

## Backend Structure

chatpdf-backend/
├── chatpdf_backend/
│ ├── settings.py
│ ├── urls.py
│ └── wsgi.py
├── accounts/
│ └── (user management)
├── documents/
│ ├── models.py (Document model)
│ ├── views.py (Upload, list, delete)
│ ├── serializers.py
│ └── utils.py (PDF text extraction)
├── chat/
│ ├── models.py (Conversation, Message)
│ ├── views.py (Chat endpoints)
│ ├── serializers.py
│ └── services.py (Gemini integration)
├── requirements.txt
└── manage.py

text

## Environment Variables

### Backend (.env)
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/chatpdf (or sqlite)
GEMINI_API_KEY=your-google-gemini-api-key
CORS_ALLOWED_ORIGINS=http://localhost:5173
MAX_UPLOAD_SIZE=10485760 # 10MB in bytes
ALLOWED_FILE_TYPES=.pdf

text

### Frontend (.env)
VITE_API_BASE_URL=http://localhost:8000/api

text

## Key Features Implementation

### PDF Text Extraction
import PyPDF2

def extract_text_from_pdf(pdf_file):
"""Extract text from uploaded PDF file"""
reader = PyPDF2.PdfReader(pdf_file)
text_by_page = []

text
for page_num, page in enumerate(reader.pages, start=1):
    text = page.extract_text()
    text_by_page.append({
        'page': page_num,
        'text': text
    })

full_text = '\n\n'.join([f"[Page {p['page']}]\n{p['text']}" for p in text_by_page])
return full_text, len(reader.pages)
text

### Document Summary Generation
def generate_summary(document_text, max_length=500):
"""Generate AI summary of document"""
prompt = f"""Provide a concise summary (max {max_length} words) of this document:

{document_text[:10000]} # First 10k chars to avoid token limits

Summary:"""

text
response = model.generate_content(prompt)
return response.text
text

### Question Answering
def answer_question(document, question, conversation_history):
"""Answer user question about document"""

text
# Build context
context = f"DOCUMENT: {document.title}\n\n{document.extracted_text}\n\n"

# Add conversation history
if conversation_history:
    context += "PREVIOUS CONVERSATION:\n"
    for msg in conversation_history:
        sender = "User" if msg.sender_type == "user" else "AI"
        context += f"{sender}: {msg.content}\n"

# Add current question
context += f"\nUser: {question}\nAI:"

# Get Gemini response
response = model.generate_content(context)

return response.text
text

## User Flow

1. **Register/Login** → User creates account
2. **Upload PDF** → Drag/drop PDF file
3. **Processing** → AI extracts text and generates summary
4. **View Dashboard** → See all uploaded documents
5. **Open Document** → View PDF + start chat
6. **Ask Questions** → Type or select suggested questions
7. **Get Answers** → AI responds with context from document
8. **Continue Conversation** → Multi-turn dialogue
9. **Manage Documents** → Delete, search, organize

## Suggested Questions Feature
Auto-generate helpful questions when document loads:
- "What is the main topic of this document?"
- "Summarize the key points"
- "What are the important dates mentioned?"
- "Who are the key people or organizations mentioned?"
- "What conclusions does the document reach?"

## Business Model

### Pricing Tiers
- **Free**: 3 documents/month, 50 questions, basic features
- **Pro**: $19/month - 50 documents/month, unlimited questions, advanced AI
- **Team**: $49/month - Unlimited documents, shared workspaces, priority support
- **Enterprise**: Custom - API access, white-label, SSO, SLA

### Target Customers
1. **Students**: Research papers, textbooks, study materials
2. **Lawyers**: Legal documents, contracts, case files
3. **Researchers**: Academic papers, reports
4. **Business**: Contracts, reports, manuals
5. **Healthcare**: Medical reports, research papers

## Success Metrics
- Upload success rate >99%
- Answer accuracy >90% (based on user feedback)
- Average response time <5 seconds
- User retention >60% after 30 days

## Security & Privacy
- Files stored securely with user isolation
- Documents deleted permanently when user requests
- No data shared with third parties
- HTTPS in production
- Rate limiting on uploads
- File type validation (PDF only)
- Max file size enforcement

## Technical Requirements

### Backend
- Python 3.11+
- Django 5.0
- PyPDF2 for PDF processing
- Google Generative AI SDK
- PostgreSQL or SQLite

### Frontend
- Node.js 18+
- React 18
- Vite
- Tailwind CSS
- Axios

## Development Workflow

Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Frontend
cd frontend
npm install
npm run dev

text

## Deployment
- Backend: Railway or Render
- Frontend: Vercel or Netlify
- File Storage: AWS S3 or Cloudinary (production)

## Important Notes
- Use Gemini 1.5 Pro (not Flash) for better document understanding
- 1M+ token context window allows full document analysis
- Include page numbers in extracted text for better references
- Implement pagination for large documents
- Cache summaries to avoid regenerating
- Add rate limiting to prevent API abuse

## Next Steps
1. Build backend with Django + Gemini integration
2. Implement PDF text extraction
3. Create React frontend with upload + chat UI
4. Test with various PDF types (scanned vs digital)
5. Deploy and launch beta
6. Gather user feedback and iterate
🚀 COMPLETE BUILD PROMPT
text
Build a complete Chat with PDF application using Django + React + Google Gemini:

=== BACKEND (Django) ===

1. CREATE Django project "chatpdf_backend"

2. CREATE apps:
   - accounts (user management)
   - documents (PDF upload/management)
   - chat (conversation with documents)

3. INSTALL dependencies in requirements.txt:
   Django==5.0
   djangorestframework==3.14.0
   dj-rest-auth==5.0.0
   django-cors-headers==4.3.0
   google-generativeai==0.3.2
   PyPDF2==3.0.1
   python-dotenv==1.0.0
   Pillow==10.1.0

4. CREATE models in documents/models.py:
   
   class Document(models.Model):
       user = models.ForeignKey(User, on_delete=models.CASCADE)
       title = models.CharField(max_length=255)
       file = models.FileField(upload_to='documents/')
       extracted_text = models.TextField()
       page_count = models.IntegerField()
       file_size = models.IntegerField()
       summary = models.TextField(blank=True)
       uploaded_at = models.DateTimeField(auto_now_add=True)

5. CREATE models in chat/models.py:
   
   class Conversation(models.Model):
       document = models.ForeignKey(Document, on_delete=models.CASCADE)
       conversation_id = models.UUIDField(default=uuid.uuid4, unique=True)
       created_at = models.DateTimeField(auto_now_add=True)
   
   class Message(models.Model):
       conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
       sender_type = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
       content = models.TextField()
       page_references = models.JSONField(null=True, blank=True)
       timestamp = models.DateTimeField(auto_now_add=True)

6. CREATE documents/utils.py for PDF processing:
   - extract_text_from_pdf(pdf_file) function using PyPDF2
   - Include page numbers: [Page 1], [Page 2], etc.
   - Handle errors gracefully

7. CREATE chat/services.py with GeminiService class:
   
   import google.generativeai as genai
   
   class GeminiService:
       def __init__(self):
           genai.configure(api_key=settings.GEMINI_API_KEY)
           self.model = genai.GenerativeModel('gemini-1.5-pro')
       
       def generate_summary(self, text):
           # Generate document summary
       
       def answer_question(self, document_text, question, history):
           # Answer question about document with context

8. CREATE API endpoints:
   
   Documents:
   - POST /api/documents/upload/ - Upload PDF (multipart)
   - GET /api/documents/ - List user's documents
   - GET /api/documents/{id}/ - Get document details
   - DELETE /api/documents/{id}/ - Delete document
   
   Chat:
   - POST /api/chat/start/ - Start conversation (input: document_id)
   - POST /api/chat/message/ - Send message (input: conversation_id, message)
   - GET /api/chat/history/{conversation_id}/ - Get chat history
   - GET /api/chat/suggestions/{document_id}/ - Get suggested questions

9. CONFIGURE settings.py:
   - MEDIA_URL and MEDIA_ROOT for file uploads
   - GEMINI_API_KEY from environment
   - CORS settings for React frontend
   - MAX_UPLOAD_SIZE = 10MB

=== FRONTEND (React) ===

1. CREATE React project with Vite and Tailwind CSS

2. CREATE components:
   
   documents/DocumentUploader.jsx:
   - Drag-and-drop zone
   - File validation (PDF only, max 10MB)
   - Upload progress indicator
   - Success/error messages
   
   documents/DocumentList.jsx:
   - Grid/list view of documents
   - Search/filter
   - Delete button
   - Click to open chat
   
   documents/DocumentCard.jsx:
   - Document title, page count, size
   - Upload date
   - Summary preview
   - Action buttons
   
   chat/ChatInterface.jsx:
   - Split view: PDF preview (left) + Chat (right)
   - Message list with user/AI bubbles
   - Input box with send button
   - Suggested questions section
   - Loading states
   
   chat/MessageBubble.jsx:
   - User messages (right-aligned, blue)
   - AI messages (left-aligned, gray)
   - Page references as clickable tags
   - Timestamp
   
   chat/SuggestedQuestions.jsx:
   - Display 5 suggested questions
   - Click to ask question
   - Different questions per document type

3. CREATE services:
   
   documentService.js:
   - uploadDocument(file)
   - listDocuments()
   - getDocument(id)
   - deleteDocument(id)
   
   chatService.js:
   - startConversation(documentId)
   - sendMessage(conversationId, message)
   - getHistory(conversationId)
   - getSuggestions(documentId)

4. CREATE pages:
   
   Dashboard.jsx:
   - Header with "Upload PDF" button
   - DocumentList component
   - Empty state if no documents
   
   ChatPage.jsx:
   - Document info header
   - ChatInterface component
   - Responsive layout (stack on mobile)

5. STYLING with Tailwind:
   - Modern, clean design
   - Blue accent color (#2563eb)
   - Card-based layout
   - Smooth animations
   - Mobile responsive

=== KEY FEATURES ===

1. PDF Upload Flow:
   - User selects PDF → Validate → Upload to backend
   - Backend extracts text with PyPDF2
   - Generate summary with Gemini
   - Save to database
   - Return document details to frontend
   - Show success + redirect to chat

2. Chat Flow:
   - User opens document → Start conversation
   - Display suggested questions
   - User asks question → Send to backend
   - Backend: Build context (full document + history) → Ask Gemini
   - Gemini analyzes document → Returns answer
   - Display answer with page references
   - Continue multi-turn conversation

3. Suggested Questions (auto-generated):
   - "What is this document about?"
   - "Summarize the key points"
   - "What are the main conclusions?"
   - "List important dates and figures"
   - "Who are the key people mentioned?"

=== ERROR HANDLING ===

- Validate PDF file type
- Handle large files (>10MB) gracefully
- Show clear error messages
- Handle Gemini API errors
- Handle malformed PDFs
- Network error retry logic

=== SECURITY ===

- User can only access their own documents
- Token authentication required
- CORS properly configured
- File upload validation
- SQL injection prevention (use ORM)
- XSS protection

=== TESTING CHECKLIST ===

- [ ] Upload PDF successfully
- [ ] Extract text from multi-page PDF
- [ ] Generate summary
- [ ] Start conversation
- [ ] Ask question and get accurate answer
- [ ] Multi-turn conversation works
- [ ] Delete document
- [ ] Responsive on mobile
- [ ] Error handling works

BUILD EVERYTHING PRODUCTION-READY IN 40 MINUTES!

Focus on:
1. PDF text extraction with page numbers
2. Gemini integration for Q&A
3. Clean chat UI
4. Document management

Start with backend, then frontend. Make it WORK!
