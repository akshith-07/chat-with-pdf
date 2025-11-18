/**
 * Workspace State Management
 */

import { create } from 'zustand';
import type { Workspace, Document, Conversation } from '../types';
import { api } from '../services/api';

interface WorkspaceState {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  documents: Document[];
  conversations: Conversation[];
  isLoading: boolean;

  // Actions
  fetchWorkspaces: () => Promise<void>;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  createWorkspace: (name: string, isTeam: boolean) => Promise<Workspace>;
  fetchDocuments: (workspaceId: number) => Promise<void>;
  fetchConversations: (workspaceId: number) => Promise<void>;
  uploadDocument: (data: any) => Promise<Document>;
  deleteDocument: (id: number) => Promise<void>;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  currentWorkspace: null,
  documents: [],
  conversations: [],
  isLoading: false,

  fetchWorkspaces: async () => {
    set({ isLoading: true });
    try {
      const workspaces = await api.getWorkspaces();
      set({ workspaces, isLoading: false });

      // Set first workspace as current if none selected
      if (!get().currentWorkspace && workspaces.length > 0) {
        set({ currentWorkspace: workspaces[0] });
      }
    } catch (error) {
      set({ isLoading: false });
      console.error('Failed to fetch workspaces:', error);
    }
  },

  setCurrentWorkspace: (workspace) => {
    set({ currentWorkspace: workspace });
    if (workspace) {
      get().fetchDocuments(workspace.id);
      get().fetchConversations(workspace.id);
    }
  },

  createWorkspace: async (name, isTeam) => {
    const workspace = await api.createWorkspace({ name, is_team: isTeam });
    set((state) => ({ workspaces: [...state.workspaces, workspace] }));
    return workspace;
  },

  fetchDocuments: async (workspaceId) => {
    try {
      const documents = await api.getDocuments({ workspace: workspaceId });
      set({ documents });
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  },

  fetchConversations: async (workspaceId) => {
    try {
      const conversations = await api.getConversations(workspaceId);
      set({ conversations });
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    }
  },

  uploadDocument: async (data) => {
    const document = await api.uploadDocument(data);
    set((state) => ({ documents: [...state.documents, document] }));
    return document;
  },

  deleteDocument: async (id) => {
    await api.deleteDocument(id);
    set((state) => ({
      documents: state.documents.filter((doc) => doc.id !== id),
    }));
  },
}));
