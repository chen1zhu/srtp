// 消息类型定义
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  generatedFiles?: string[];
}

// 对话类型定义
export interface Conversation {
  id: string; // frontend local id
  // 新增：后端对话ID（由后端返回）。用于 /chat/continue/{conversation_id}
  serverId?: string;
  title: string;
  messages: Message[];
  lastActive: Date;
  requiresFollowUp?: boolean;
}

// API响应类型
export interface ChatResponse {
  conversation_id: string;
  answer: string;
  requires_follow_up: boolean;
  generated_files: string[];
}

// 侧边栏状态
export interface SidebarState {
  isOpen: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
}
