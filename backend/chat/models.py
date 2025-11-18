from django.db import models
from django.contrib.auth.models import User
from documents.models import Document, Workspace
import uuid


class Conversation(models.Model):
    """Enhanced conversation model supporting multi-document chat"""

    id = models.AutoField(primary_key=True)
    conversation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='conversations')
    documents = models.ManyToManyField(Document, related_name='conversations')  # Multi-document support

    # Conversation metadata
    title = models.CharField(max_length=255, blank=True)  # Auto-generated from first question
    is_shared = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_conversations', blank=True)

    # Timestamps and ownership
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['workspace', '-last_activity']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['conversation_id']),
        ]

    def __str__(self):
        return f"{self.title or 'Conversation'} - {self.conversation_id}"

    def get_document_count(self):
        """Get number of documents in conversation"""
        return self.documents.count()


class Message(models.Model):
    """Enhanced message model with citations and metadata"""

    SENDER_TYPES = [
        ('user', 'User'),
        ('ai', 'AI Assistant'),
    ]

    id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    content = models.TextField()

    # Advanced citations
    citations = models.JSONField(default=list, blank=True)
    # Format: [{"document_id": 1, "document_title": "...", "page": 5, "quote": "...", "start": 120, "end": 350}]

    # Response metadata (for AI messages)
    confidence_score = models.FloatField(null=True, blank=True)  # AI confidence in answer
    processing_time = models.FloatField(null=True, blank=True)  # Time to generate response (seconds)
    token_count = models.IntegerField(null=True, blank=True)  # Tokens used for this response

    # Voice/audio support
    audio_file = models.FileField(upload_to='audio/%Y/%m/', null=True, blank=True)
    audio_duration = models.FloatField(null=True, blank=True)  # In seconds

    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['sender_type']),
        ]

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.sender_type}: {preview}"

    def get_citation_count(self):
        """Get number of citations in message"""
        return len(self.citations) if self.citations else 0


class SuggestedQuestion(models.Model):
    """AI-generated suggested questions for documents"""

    QUESTION_TYPES = [
        ('summary', 'Summary'),
        ('detail', 'Detail'),
        ('analysis', 'Analysis'),
        ('comparison', 'Comparison'),
    ]

    id = models.AutoField(primary_key=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='suggested_questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    order = models.IntegerField(default=0)  # Display order
    times_used = models.IntegerField(default=0)  # Track popularity
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-times_used']
        indexes = [
            models.Index(fields=['document', 'order']),
        ]

    def __str__(self):
        return f"{self.document.title[:30]} - {self.question[:50]}"


class ConversationExport(models.Model):
    """Track exported conversations"""

    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('markdown', 'Markdown'),
        ('txt', 'Plain Text'),
    ]

    id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='exports')
    format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    file = models.FileField(upload_to='exports/%Y/%m/')
    file_size = models.IntegerField(default=0)  # In bytes
    include_citations = models.BooleanField(default=True)
    include_document_excerpts = models.BooleanField(default=True)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.conversation.title} - {self.format.upper()} - {self.created_at.strftime('%Y-%m-%d')}"


class MessageFeedback(models.Model):
    """User feedback on AI responses for quality improvement"""

    FEEDBACK_TYPES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
        ('inaccurate', 'Inaccurate'),
        ('incomplete', 'Incomplete'),
    ]

    id = models.AutoField(primary_key=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['message', 'user']

    def __str__(self):
        return f"{self.feedback_type} - {self.message.id}"
