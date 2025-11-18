/**
 * API Service Layer
 * Handles all communication with the Django backend
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  User,
  Workspace,
  Folder,
  Document,
  DocumentUpload,
  Conversation,
  Message,
  StartConversation,
  SendMessage,
  SuggestedQuestion,
  DocumentComparison,
  UsageAnalytics,
  DocumentStats,
  LoginCredentials,
  RegisterData,
  AuthTokens,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Token ${token}`;
      }
      return config;
    });

    // Handle response errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // ============================================================================
  // Authentication
  // ============================================================================

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const response = await this.client.post('/auth/login/', credentials);
    const token = response.data.key || response.data.access_token;
    localStorage.setItem('auth_token', token);
    return response.data;
  }

  async register(data: RegisterData): Promise<AuthTokens> {
    const response = await this.client.post('/auth/registration/', data);
    const token = response.data.key || response.data.access_token;
    localStorage.setItem('auth_token', token);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout/');
    localStorage.removeItem('auth_token');
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/user/');
    return response.data;
  }

  // ============================================================================
  // Workspaces
  // ============================================================================

  async getWorkspaces(): Promise<Workspace[]> {
    const response = await this.client.get('/workspaces/');
    return response.data.results || response.data;
  }

  async getWorkspace(id: number): Promise<Workspace> {
    const response = await this.client.get(`/workspaces/${id}/`);
    return response.data;
  }

  async createWorkspace(data: Partial<Workspace>): Promise<Workspace> {
    const response = await this.client.post('/workspaces/', data);
    return response.data;
  }

  async updateWorkspace(id: number, data: Partial<Workspace>): Promise<Workspace> {
    const response = await this.client.patch(`/workspaces/${id}/`, data);
    return response.data;
  }

  async deleteWorkspace(id: number): Promise<void> {
    await this.client.delete(`/workspaces/${id}/`);
  }

  async addWorkspaceMember(workspaceId: number, userId: number): Promise<void> {
    await this.client.post(`/workspaces/${workspaceId}/add_member/`, { user_id: userId });
  }

  // ============================================================================
  // Folders
  // ============================================================================

  async getFolders(workspaceId?: number): Promise<Folder[]> {
    const params = workspaceId ? { workspace: workspaceId } : {};
    const response = await this.client.get('/folders/', { params });
    return response.data.results || response.data;
  }

  async createFolder(data: Partial<Folder>): Promise<Folder> {
    const response = await this.client.post('/folders/', data);
    return response.data;
  }

  async deleteFolder(id: number): Promise<void> {
    await this.client.delete(`/folders/${id}/`);
  }

  // ============================================================================
  // Documents
  // ============================================================================

  async getDocuments(params?: {
    workspace?: number;
    folder?: number;
    type?: string;
    status?: string;
    search?: string;
  }): Promise<Document[]> {
    const response = await this.client.get('/documents/', { params });
    return response.data.results || response.data;
  }

  async getDocument(id: number): Promise<Document> {
    const response = await this.client.get(`/documents/${id}/`);
    return response.data;
  }

  async uploadDocument(data: DocumentUpload): Promise<Document> {
    const formData = new FormData();
    formData.append('workspace', data.workspace.toString());
    if (data.folder) {
      formData.append('folder', data.folder.toString());
    }
    formData.append('title', data.title);
    formData.append('file', data.file);

    const response = await this.client.post('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async deleteDocument(id: number): Promise<void> {
    await this.client.delete(`/documents/${id}/`);
  }

  async getDocumentSummary(id: number): Promise<any> {
    const response = await this.client.get(`/documents/${id}/summary/`);
    return response.data;
  }

  async getDocumentHighlights(id: number, page?: number): Promise<any[]> {
    const params = page ? { page } : {};
    const response = await this.client.get(`/documents/${id}/highlights/`, { params });
    return response.data;
  }

  async searchDocuments(query: string, workspaceId?: number): Promise<any> {
    const params: any = { q: query };
    if (workspaceId) params.workspace = workspaceId;
    const response = await this.client.get('/documents/search/', { params });
    return response.data;
  }

  async compareDocuments(
    workspaceId: number,
    documentIds: number[],
    comparisonType: string
  ): Promise<DocumentComparison> {
    const response = await this.client.post('/documents/compare/', {
      workspace: workspaceId,
      document_ids: documentIds,
      comparison_type: comparisonType,
    });
    return response.data;
  }

  async getDocumentStats(workspaceId?: number): Promise<DocumentStats> {
    const params = workspaceId ? { workspace: workspaceId } : {};
    const response = await this.client.get('/documents/stats/', { params });
    return response.data;
  }

  // ============================================================================
  // Chat / Conversations
  // ============================================================================

  async startConversation(data: StartConversation): Promise<Conversation> {
    const response = await this.client.post('/chat/start/', data);
    return response.data;
  }

  async sendMessage(data: SendMessage): Promise<any> {
    const response = await this.client.post('/chat/message/', data);
    return response.data;
  }

  async getConversations(workspaceId?: number): Promise<Conversation[]> {
    const params = workspaceId ? { workspace: workspaceId } : {};
    const response = await this.client.get('/chat/conversations/', { params });
    return response.data.results || response.data;
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await this.client.get(`/chat/conversations/${conversationId}/`);
    return response.data;
  }

  async getSuggestedQuestions(documentId: number): Promise<SuggestedQuestion[]> {
    const response = await this.client.get('/chat/suggestions/', {
      params: { document_id: documentId },
    });
    return response.data;
  }

  // ============================================================================
  // Analytics
  // ============================================================================

  async getAnalytics(params?: {
    workspace?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<UsageAnalytics[]> {
    const response = await this.client.get('/analytics/', { params });
    return response.data.results || response.data;
  }

  async getAnalyticsSummary(workspaceId?: number): Promise<any> {
    const params = workspaceId ? { workspace: workspaceId } : {};
    const response = await this.client.get('/analytics/summary/', { params });
    return response.data;
  }
}

export const api = new APIService();
export default api;
