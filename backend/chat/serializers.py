"""
Serializers for chat app
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Conversation,
    Message,
    SuggestedQuestion,
    ConversationExport,
    MessageFeedback
)
from documents.models import Document
from documents.serializers import DocumentListSerializer, UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    """Message serializer"""
    citation_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender_type', 'content', 'citations',
            'confidence_score', 'processing_time', 'token_count',
            'audio_file', 'audio_duration', 'timestamp', 'is_edited',
            'citation_count'
        ]
        read_only_fields = [
            'id', 'timestamp', 'confidence_score', 'processing_time',
            'token_count', 'is_edited'
        ]

    def get_citation_count(self, obj):
        return obj.get_citation_count()


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight conversation serializer for lists"""
    document_count = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_id', 'workspace', 'title', 'is_shared',
            'document_count', 'message_count', 'last_message',
            'created_by', 'created_at', 'last_activity'
        ]
        read_only_fields = ['id', 'conversation_id', 'created_at', 'last_activity']

    def get_document_count(self, obj):
        return obj.get_document_count()

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'sender_type': last_msg.sender_type,
                'content': last_msg.content[:100],
                'timestamp': last_msg.timestamp
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed conversation serializer with messages"""
    documents = DocumentListSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    shared_with = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_id', 'workspace', 'documents', 'title',
            'is_shared', 'shared_with', 'messages', 'created_by',
            'created_at', 'last_activity'
        ]
        read_only_fields = ['id', 'conversation_id', 'created_at', 'last_activity']


class StartConversationSerializer(serializers.Serializer):
    """Serializer for starting a new conversation"""
    workspace_id = serializers.IntegerField(required=True)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1
    )
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_document_ids(self, value):
        """Validate that documents exist and user has access"""
        if not value:
            raise serializers.ValidationError("At least one document is required")

        # Check if documents exist
        from documents.models import Document
        documents = Document.objects.filter(id__in=value)

        if documents.count() != len(value):
            raise serializers.ValidationError("Some documents do not exist")

        return value

    def create(self, validated_data):
        """Create new conversation"""
        from documents.models import Document, Workspace

        workspace = Workspace.objects.get(id=validated_data['workspace_id'])
        user = self.context['request'].user

        # Create conversation
        conversation = Conversation.objects.create(
            workspace=workspace,
            title=validated_data.get('title', ''),
            created_by=user
        )

        # Add documents
        documents = Document.objects.filter(id__in=validated_data['document_ids'])
        conversation.documents.set(documents)

        # Auto-generate title if not provided
        if not conversation.title:
            if documents.count() == 1:
                conversation.title = f"Chat: {documents.first().title[:50]}"
            else:
                conversation.title = f"Multi-document chat ({documents.count()} documents)"
            conversation.save()

        return conversation


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message"""
    conversation_id = serializers.UUIDField(required=True)
    message = serializers.CharField(required=True, min_length=1)

    def validate_conversation_id(self, value):
        """Validate conversation exists"""
        try:
            conversation = Conversation.objects.get(conversation_id=value)
            # Check user has access
            user = self.context['request'].user
            if conversation.created_by != user and user not in conversation.shared_with.all():
                raise serializers.ValidationError("You don't have access to this conversation")
        except Conversation.DoesNotExist:
            raise serializers.ValidationError("Conversation not found")

        return value

    def create(self, validated_data):
        """Send message and get AI response"""
        from .services import GeminiService
        import time

        user = self.context['request'].user
        conversation = Conversation.objects.get(
            conversation_id=validated_data['conversation_id']
        )

        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            sender_type='user',
            content=validated_data['message']
        )

        # Get conversation history
        history = list(conversation.messages.order_by('timestamp'))

        # Get AI response
        try:
            start_time = time.time()
            gemini = GeminiService()

            documents = list(conversation.documents.all())

            result = gemini.multi_document_chat(
                documents=documents,
                question=validated_data['message'],
                history=history[:-1]  # Exclude current message
            )

            processing_time = time.time() - start_time

            # Create AI message
            ai_message = Message.objects.create(
                conversation=conversation,
                sender_type='ai',
                content=result['answer'],
                citations=result.get('citations', []),
                confidence_score=result.get('confidence_score'),
                processing_time=processing_time,
                token_count=result.get('token_count')
            )

            # Update document question count
            for doc in documents:
                doc.question_count += 1
                doc.save(update_fields=['question_count'])

            # Update analytics
            from documents.tasks import update_usage_analytics
            update_usage_analytics.delay(
                workspace_id=conversation.workspace.id,
                user_id=user.id,
                metric_type='questions_asked'
            )

            return {
                'user_message': user_message,
                'ai_message': ai_message,
                'conversation': conversation
            }

        except Exception as e:
            # Create error message
            ai_message = Message.objects.create(
                conversation=conversation,
                sender_type='ai',
                content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
            )

            return {
                'user_message': user_message,
                'ai_message': ai_message,
                'conversation': conversation,
                'error': str(e)
            }


class SuggestedQuestionSerializer(serializers.ModelSerializer):
    """Suggested question serializer"""

    class Meta:
        model = SuggestedQuestion
        fields = [
            'id', 'document', 'question', 'question_type',
            'order', 'times_used', 'created_at'
        ]
        read_only_fields = ['id', 'times_used', 'created_at']


class ConversationExportSerializer(serializers.ModelSerializer):
    """Conversation export serializer"""
    file_url = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = ConversationExport
        fields = [
            'id', 'conversation', 'format', 'file', 'file_url', 'file_size',
            'include_citations', 'include_document_excerpts',
            'created_by', 'created_at', 'download_count'
        ]
        read_only_fields = ['id', 'file', 'file_size', 'created_at', 'download_count']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class MessageFeedbackSerializer(serializers.ModelSerializer):
    """Message feedback serializer"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = MessageFeedback
        fields = ['id', 'message', 'user', 'feedback_type', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
