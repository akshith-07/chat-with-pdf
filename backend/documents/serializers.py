"""
Serializers for documents app
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Workspace,
    Folder,
    Document,
    DocumentHighlight,
    DocumentComparison,
    UsageAnalytics
)


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class WorkspaceSerializer(serializers.ModelSerializer):
    """Workspace serializer"""
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    document_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'owner', 'members', 'is_team', 'settings',
            'created_at', 'updated_at', 'document_count', 'member_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_member_count(self, obj):
        return obj.members.count()


class FolderSerializer(serializers.ModelSerializer):
    """Folder serializer with hierarchical structure support"""
    document_count = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'workspace', 'parent', 'color',
            'created_at', 'updated_at', 'document_count',
            'subfolder_count', 'path'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_subfolder_count(self, obj):
        return obj.subfolders.count()

    def get_path(self, obj):
        """Get full folder path"""
        path = [obj.name]
        current = obj.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' / '.join(path)


class DocumentHighlightSerializer(serializers.ModelSerializer):
    """Document highlight serializer"""
    class Meta:
        model = DocumentHighlight
        fields = [
            'id', 'document', 'page', 'content', 'highlight_type',
            'position', 'color', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight document serializer for lists"""
    uploaded_by = UserSerializer(read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'workspace', 'folder', 'folder_name',
            'page_count', 'file_size', 'document_type', 'sentiment',
            'processing_status', 'uploaded_by', 'uploaded_at',
            'last_accessed', 'view_count', 'question_count'
        ]
        read_only_fields = ['id', 'uploaded_at', 'processing_status']


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Detailed document serializer with all metadata"""
    uploaded_by = UserSerializer(read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    highlights = DocumentHighlightSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'workspace', 'folder', 'folder_name', 'title', 'file',
            'file_url', 'extracted_text', 'page_count', 'file_size',
            'language', 'summary', 'key_entities', 'key_topics',
            'important_dates', 'sentiment', 'document_type',
            'search_keywords', 'processing_status', 'ocr_required',
            'processing_error', 'view_count', 'question_count',
            'last_accessed', 'uploaded_by', 'uploaded_at',
            'updated_at', 'highlights'
        ]
        read_only_fields = [
            'id', 'extracted_text', 'page_count', 'file_size',
            'language', 'summary', 'key_entities', 'key_topics',
            'important_dates', 'sentiment', 'document_type',
            'processing_status', 'ocr_required', 'processing_error',
            'view_count', 'question_count', 'last_accessed',
            'uploaded_at', 'updated_at'
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document upload"""

    class Meta:
        model = Document
        fields = ['id', 'workspace', 'folder', 'title', 'file']
        read_only_fields = ['id']

    def validate_file(self, value):
        """Validate PDF file"""
        from .utils import validate_pdf, get_file_size
        from django.conf import settings

        # Validate file
        is_valid, error_message = validate_pdf(value, max_size_mb=10)
        if not is_valid:
            raise serializers.ValidationError(error_message)

        return value

    def create(self, validated_data):
        """Create document and trigger processing"""
        from .utils import get_file_size

        # Add uploaded_by
        validated_data['uploaded_by'] = self.context['request'].user

        # Get file size
        file_obj = validated_data.get('file')
        if file_obj:
            validated_data['file_size'] = get_file_size(file_obj)

        # Create document
        document = super().create(validated_data)

        # Trigger async processing
        from .tasks import process_document
        process_document.delay(document.id)

        return document


class DocumentComparisonSerializer(serializers.ModelSerializer):
    """Document comparison serializer"""
    documents = DocumentListSerializer(many=True, read_only=True)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = DocumentComparison
        fields = [
            'id', 'workspace', 'documents', 'document_ids',
            'comparison_type', 'results', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'results', 'created_at']

    def create(self, validated_data):
        """Create comparison and run AI analysis"""
        from chat.services import GeminiService

        document_ids = validated_data.pop('document_ids')
        validated_data['created_by'] = self.context['request'].user

        # Create comparison object
        comparison = DocumentComparison.objects.create(**validated_data)

        # Get documents
        documents = Document.objects.filter(
            id__in=document_ids,
            workspace=validated_data['workspace']
        )

        if documents.count() < 2:
            raise serializers.ValidationError("At least 2 documents required for comparison")

        comparison.documents.set(documents)

        # Run AI comparison
        try:
            gemini = GeminiService()
            results = gemini.compare_documents(
                list(documents),
                validated_data['comparison_type']
            )
            comparison.results = results
            comparison.save()
        except Exception as e:
            comparison.results = {'error': str(e)}
            comparison.save()

        return comparison


class UsageAnalyticsSerializer(serializers.ModelSerializer):
    """Usage analytics serializer"""
    user = UserSerializer(read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = UsageAnalytics
        fields = [
            'id', 'workspace', 'workspace_name', 'user', 'date',
            'documents_uploaded', 'questions_asked', 'conversations_started',
            'tokens_used', 'processing_time'
        ]
        read_only_fields = ['id']
