"""
API Views for documents app
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    Workspace,
    Folder,
    Document,
    DocumentHighlight,
    DocumentComparison,
    UsageAnalytics
)
from .serializers import (
    WorkspaceSerializer,
    FolderSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentHighlightSerializer,
    DocumentComparisonSerializer,
    UsageAnalyticsSerializer
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """Workspace management"""
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        """Get workspaces user owns or is member of"""
        user = self.request.user
        return Workspace.objects.filter(
            Q(owner=user) | Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        """Create workspace with current user as owner"""
        workspace = serializer.save(owner=self.request.user)
        workspace.members.add(self.request.user)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add member to workspace"""
        workspace = self.get_object()

        # Only owner can add members
        if workspace.owner != request.user:
            return Response(
                {'error': 'Only workspace owner can add members'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
            workspace.members.add(user)
            return Response({'message': 'Member added successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class FolderViewSet(viewsets.ModelViewSet):
    """Folder management"""
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Get folders in workspaces user has access to"""
        user = self.request.user
        workspace_id = self.request.query_params.get('workspace')

        queryset = Folder.objects.filter(
            workspace__members=user
        )

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        return queryset


class DocumentViewSet(viewsets.ModelViewSet):
    """Document management with enterprise features"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'extracted_text', 'search_keywords']
    ordering_fields = ['uploaded_at', 'title', 'page_count', 'view_count']

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return DocumentUploadSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return DocumentDetailSerializer
        return DocumentListSerializer

    def get_queryset(self):
        """Get documents user has access to"""
        user = self.request.user
        queryset = Document.objects.filter(
            workspace__members=user
        ).select_related('uploaded_by', 'folder', 'workspace')

        # Filter by workspace
        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        # Filter by folder
        folder_id = self.request.query_params.get('folder')
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        # Filter by document type
        doc_type = self.request.query_params.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        # Filter by processing status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(processing_status=status_filter)

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Get document and increment view count"""
        document = self.get_object()
        document.view_count += 1
        document.last_accessed = timezone.now()
        document.save(update_fields=['view_count', 'last_accessed'])

        serializer = self.get_serializer(document)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def highlights(self, request, pk=None):
        """Get AI-generated highlights for document"""
        document = self.get_object()
        highlights = document.highlights.all()

        # Filter by page if specified
        page = request.query_params.get('page')
        if page:
            highlights = highlights.filter(page=int(page))

        serializer = DocumentHighlightSerializer(highlights, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_highlights(self, request, pk=None):
        """Trigger highlight generation for document"""
        document = self.get_object()

        # Get page numbers to process
        pages = request.data.get('pages', None)

        # Trigger async task
        from .tasks import generate_document_highlights
        task = generate_document_highlights.delay(document.id, pages)

        return Response({
            'message': 'Highlight generation started',
            'task_id': task.id
        })

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get document summary"""
        document = self.get_object()
        return Response({
            'summary': document.summary,
            'key_entities': document.key_entities,
            'key_topics': document.key_topics,
            'important_dates': document.important_dates,
            'document_type': document.document_type,
            'sentiment': document.sentiment
        })

    @action(detail=False, methods=['post'])
    def compare(self, request):
        """Compare multiple documents"""
        serializer = DocumentComparisonSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        comparison = serializer.save()

        return Response(
            DocumentComparisonSerializer(comparison, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search across documents"""
        query = request.query_params.get('q', '')
        workspace_id = request.query_params.get('workspace')

        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Search in title, extracted text, and keywords
        queryset = self.get_queryset()

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        results = queryset.filter(
            Q(title__icontains=query) |
            Q(extracted_text__icontains=query) |
            Q(search_keywords__icontains=query) |
            Q(key_topics__icontains=query)
        )

        serializer = DocumentListSerializer(
            results,
            many=True,
            context={'request': request}
        )

        return Response({
            'query': query,
            'count': results.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics for workspace"""
        workspace_id = request.query_params.get('workspace')

        queryset = self.get_queryset()

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        total_docs = queryset.count()
        total_pages = sum(doc.page_count for doc in queryset)
        total_questions = sum(doc.question_count for doc in queryset)

        # Count by type
        by_type = {}
        for doc in queryset:
            doc_type = doc.document_type or 'other'
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

        # Count by status
        by_status = {}
        for doc in queryset:
            by_status[doc.processing_status] = by_status.get(doc.processing_status, 0) + 1

        return Response({
            'total_documents': total_docs,
            'total_pages': total_pages,
            'total_questions': total_questions,
            'by_type': by_type,
            'by_status': by_status
        })


class DocumentComparisonViewSet(viewsets.ReadOnlyModelViewSet):
    """View document comparisons"""
    serializer_class = DocumentComparisonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get comparisons in user's workspaces"""
        user = self.request.user
        return DocumentComparison.objects.filter(
            workspace__members=user
        ).order_by('-created_at')


class UsageAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """Usage analytics"""
    serializer_class = UsageAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']

    def get_queryset(self):
        """Get analytics for user's workspaces"""
        user = self.request.user
        workspace_id = self.request.query_params.get('workspace')

        queryset = UsageAnalytics.objects.filter(
            workspace__members=user
        )

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get analytics summary"""
        workspace_id = request.query_params.get('workspace')

        queryset = self.get_queryset()

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        total_docs = sum(a.documents_uploaded for a in queryset)
        total_questions = sum(a.questions_asked for a in queryset)
        total_conversations = sum(a.conversations_started for a in queryset)
        total_tokens = sum(a.tokens_used for a in queryset)

        return Response({
            'total_documents_uploaded': total_docs,
            'total_questions_asked': total_questions,
            'total_conversations_started': total_conversations,
            'total_tokens_used': total_tokens
        })
