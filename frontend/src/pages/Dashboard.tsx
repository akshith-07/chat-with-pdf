import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useWorkspaceStore } from '../store/workspaceStore';
import {
  FileText,
  Upload,
  MessageSquare,
  BarChart3,
  Settings,
  LogOut,
  Folder,
  Search,
  Plus,
  Loader2,
} from 'lucide-react';
import type { Document } from '../types';

function Sidebar() {
  const { user, logout } = useAuthStore();
  const { workspaces, currentWorkspace, setCurrentWorkspace } = useWorkspaceStore();

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Logo */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <FileText className="w-8 h-8 text-primary-600" />
          <span className="font-bold text-xl">ChatPDF AI</span>
        </div>
      </div>

      {/* Workspace Selector */}
      <div className="p-4 border-b border-gray-200">
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Workspace
        </label>
        <select
          className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          value={currentWorkspace?.id || ''}
          onChange={(e) => {
            const ws = workspaces.find((w) => w.id === Number(e.target.value));
            setCurrentWorkspace(ws || null);
          }}
        >
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.id}>
              {ws.name} {ws.is_team ? '(Team)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <NavLink icon={<FileText className="w-5 h-5" />} to="/dashboard" text="Documents" />
        <NavLink icon={<MessageSquare className="w-5 h-5" />} to="/dashboard/chat" text="Conversations" />
        <NavLink icon={<BarChart3 className="w-5 h-5" />} to="/dashboard/analytics" text="Analytics" />
        <NavLink icon={<Settings className="w-5 h-5" />} to="/dashboard/settings" text="Settings" />
      </nav>

      {/* User Menu */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-medium">
              {user?.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.first_name || user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function NavLink({ icon, to, text }: { icon: React.ReactNode; to: string; text: string }) {
  const isActive = window.location.pathname === to;

  return (
    <a
      href={to}
      className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
        isActive
          ? 'bg-primary-50 text-primary-700'
          : 'text-gray-700 hover:bg-gray-100'
      }`}
    >
      {icon}
      <span className="font-medium">{text}</span>
    </a>
  );
}

function DocumentsView() {
  const { documents, uploadDocument, deleteDocument, currentWorkspace } = useWorkspaceStore();
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentWorkspace) return;

    setIsUploading(true);
    try {
      await uploadDocument({
        workspace: currentWorkspace.id,
        title: file.name.replace('.pdf', ''),
        file,
      });
    } catch (error) {
      alert('Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const filteredDocuments = documents.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <label className="btn-primary cursor-pointer flex items-center">
            <Upload className="w-4 h-4 mr-2" />
            {isUploading ? 'Uploading...' : 'Upload PDF'}
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileUpload}
              disabled={isUploading}
            />
          </label>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search documents..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Documents Grid */}
      <div className="flex-1 p-6 overflow-y-auto">
        {filteredDocuments.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
            <p className="text-gray-500">Upload your first PDF to get started</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredDocuments.map((doc) => (
              <DocumentCard key={doc.id} document={doc} onDelete={() => deleteDocument(doc.id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentCard({ document, onDelete }: { document: Document; onDelete: () => void }) {
  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <FileText className="w-8 h-8 text-primary-600" />
        <span
          className={`text-xs px-2 py-1 rounded-full ${statusColors[document.processing_status]}`}
        >
          {document.processing_status}
        </span>
      </div>

      <h3 className="font-medium text-gray-900 mb-1 truncate">{document.title}</h3>
      <p className="text-sm text-gray-500 mb-3">
        {document.page_count} pages • {(document.file_size / 1024).toFixed(0)} KB
      </p>

      {document.processing_status === 'completed' && (
        <>
          <p className="text-xs text-gray-600 line-clamp-2 mb-3">{document.summary}</p>
          <div className="flex gap-2">
            <a
              href={`/dashboard/chat?doc=${document.id}`}
              className="flex-1 btn-primary text-center text-sm py-2"
            >
              Chat
            </a>
            <button
              onClick={onDelete}
              className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg"
            >
              Delete
            </button>
          </div>
        </>
      )}

      {document.processing_status === 'processing' && (
        <div className="flex items-center text-sm text-gray-500">
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Processing...
        </div>
      )}
    </div>
  );
}

function ConversationsPlaceholder() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Conversations</h3>
        <p className="text-gray-500">Start chatting with your documents</p>
      </div>
    </div>
  );
}

function AnalyticsPlaceholder() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <BarChart3 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Analytics</h3>
        <p className="text-gray-500">View your usage statistics</p>
      </div>
    </div>
  );
}

function SettingsPlaceholder() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <Settings className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Settings</h3>
        <p className="text-gray-500">Manage your account and workspace settings</p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const { fetchWorkspaces } = useWorkspaceStore();

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Routes>
          <Route path="/" element={<DocumentsView />} />
          <Route path="/chat" element={<ConversationsPlaceholder />} />
          <Route path="/analytics" element={<AnalyticsPlaceholder />} />
          <Route path="/settings" element={<SettingsPlaceholder />} />
        </Routes>
      </div>
    </div>
  );
}
