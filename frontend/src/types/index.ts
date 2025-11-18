// Type definitions for the ChatPDF application

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface Workspace {
  id: number;
  name: string;
  owner: User;
  members: User[];
  is_team: boolean;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
  document_count: number;
  member_count: number;
}

export interface Folder {
  id: number;
  name: string;
  workspace: number;
  parent: number | null;
  color: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  subfolder_count: number;
  path: string;
}

export interface Document {
  id: number;
  workspace: number;
  folder: number | null;
  folder_name?: string;
  title: string;
  file: string;
  file_url?: string;
  extracted_text?: string;
  page_count: number;
  file_size: number;
  language: string;
  summary: string;
  key_entities: {
    people: string[];
    organizations: string[];
    locations: string[];
  };
  key_topics: string[];
  important_dates: string[];
  sentiment: string;
  document_type: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  ocr_required: boolean;
  processing_error: string;
  view_count: number;
  question_count: number;
  last_accessed: string | null;
  uploaded_by: User;
  uploaded_at: string;
  updated_at: string;
}

export interface DocumentHighlight {
  id: number;
  document: number;
  page: number;
  content: string;
  highlight_type: 'key_point' | 'definition' | 'statistic' | 'conclusion' | 'important';
  position: Record<string, any>;
  color: string;
  created_at: string;
}

export interface Citation {
  document_id: number;
  document_title: string;
  page: number;
  quote?: string;
  start?: number;
  end?: number;
}

export interface Message {
  id: number;
  conversation: number;
  sender_type: 'user' | 'ai';
  content: string;
  citations: Citation[];
  confidence_score: number | null;
  processing_time: number | null;
  token_count: number | null;
  timestamp: string;
  is_edited: boolean;
  citation_count: number;
}

export interface Conversation {
  id: number;
  conversation_id: string;
  workspace: number;
  documents: Document[];
  title: string;
  is_shared: boolean;
  shared_with: User[];
  messages: Message[];
  created_by: User;
  created_at: string;
  last_activity: string;
}

export interface SuggestedQuestion {
  id: number;
  document: number;
  question: string;
  question_type: 'summary' | 'detail' | 'analysis' | 'comparison';
  order: number;
  times_used: number;
  created_at: string;
}

export interface DocumentComparison {
  id: number;
  workspace: number;
  documents: Document[];
  comparison_type: 'similarities' | 'differences' | 'timeline' | 'synthesis';
  results: {
    comparison_type: string;
    analysis: string;
    document_count: number;
    document_titles: string[];
  };
  created_by: User;
  created_at: string;
}

export interface UsageAnalytics {
  id: number;
  workspace: number;
  workspace_name: string;
  user: User;
  date: string;
  documents_uploaded: number;
  questions_asked: number;
  conversations_started: number;
  tokens_used: number;
  processing_time: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password1: string;
  password2: string;
  first_name?: string;
  last_name?: string;
}

export interface DocumentUpload {
  workspace: number;
  folder?: number;
  title: string;
  file: File;
}

export interface StartConversation {
  workspace_id: number;
  document_ids: number[];
  title?: string;
}

export interface SendMessage {
  conversation_id: string;
  message: string;
}

export interface DocumentStats {
  total_documents: number;
  total_pages: number;
  total_questions: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}
