from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid


class Workspace(models.Model):
    """Workspace for organizing documents - supports personal and team workspaces"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    members = models.ManyToManyField(User, related_name='workspaces', blank=True)
    is_team = models.BooleanField(default=False)
    settings = models.JSONField(default=dict, blank=True)  # Custom AI settings, preferences
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_team']),
        ]

    def __str__(self):
        return f"{self.name} ({'Team' if self.is_team else 'Personal'})"


class Folder(models.Model):
    """Hierarchical folder structure for organizing documents"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subfolders')
    color = models.CharField(max_length=7, default='#2563eb')  # Hex color for UI
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['workspace', 'parent']),
        ]

    def __str__(self):
        return f"{self.workspace.name}/{self.name}"


class Document(models.Model):
    """Enhanced document model with AI-powered metadata and processing"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    DOCUMENT_TYPES = [
        ('contract', 'Contract'),
        ('research', 'Research Paper'),
        ('report', 'Report'),
        ('manual', 'Manual'),
        ('legal', 'Legal Document'),
        ('financial', 'Financial Document'),
        ('educational', 'Educational'),
        ('other', 'Other'),
    ]

    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('mixed', 'Mixed'),
    ]

    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='documents')
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL, related_name='documents')

    # Basic info
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )

    # Text extraction
    extracted_text = models.TextField(blank=True)
    page_count = models.IntegerField(default=0)
    file_size = models.IntegerField(default=0)  # In bytes
    language = models.CharField(max_length=10, default='en')

    # AI-generated metadata
    summary = models.TextField(blank=True)
    key_entities = models.JSONField(default=dict, blank=True)  # {people: [], organizations: [], locations: []}
    key_topics = models.JSONField(default=list, blank=True)  # List of main topics
    important_dates = models.JSONField(default=list, blank=True)  # List of dates mentioned
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral', blank=True)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='other', blank=True)

    # Search optimization
    embeddings = models.JSONField(null=True, blank=True)  # Vector embeddings for semantic search
    search_keywords = models.TextField(blank=True)  # Extracted keywords for search

    # Processing status
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ocr_required = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)

    # Usage statistics
    view_count = models.IntegerField(default=0)
    question_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['workspace', 'folder']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['document_type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.page_count} pages)"


class DocumentHighlight(models.Model):
    """AI-generated highlights of key sections in documents"""

    HIGHLIGHT_TYPES = [
        ('key_point', 'Key Point'),
        ('definition', 'Definition'),
        ('statistic', 'Statistic'),
        ('conclusion', 'Conclusion'),
        ('important', 'Important'),
    ]

    id = models.AutoField(primary_key=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='highlights')
    page = models.IntegerField()
    content = models.TextField()
    highlight_type = models.CharField(max_length=20, choices=HIGHLIGHT_TYPES)
    position = models.JSONField(default=dict)  # {x, y, width, height} for PDF positioning
    color = models.CharField(max_length=7, default='#FFEB3B')  # Yellow default
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page', 'id']
        indexes = [
            models.Index(fields=['document', 'page']),
        ]

    def __str__(self):
        return f"{self.document.title} - Page {self.page} ({self.highlight_type})"


class DocumentComparison(models.Model):
    """Store results of document comparisons"""

    COMPARISON_TYPES = [
        ('similarities', 'Similarities'),
        ('differences', 'Differences'),
        ('timeline', 'Timeline'),
        ('synthesis', 'Synthesis'),
    ]

    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='comparisons')
    documents = models.ManyToManyField(Document, related_name='comparisons')
    comparison_type = models.CharField(max_length=50, choices=COMPARISON_TYPES)
    results = models.JSONField(default=dict)  # Stores comparison analysis
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comparison ({self.comparison_type}) - {self.created_at.strftime('%Y-%m-%d')}"


class UsageAnalytics(models.Model):
    """Track usage analytics per workspace and user"""

    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='analytics')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()

    # Metrics
    documents_uploaded = models.IntegerField(default=0)
    questions_asked = models.IntegerField(default=0)
    conversations_started = models.IntegerField(default=0)
    tokens_used = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0)  # In seconds

    class Meta:
        unique_together = ['workspace', 'user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['workspace', 'date']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.workspace.name} - {self.date}"
