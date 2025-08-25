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

// 流式事件类型（SSE）
export type StreamEventType =
  | 'user_message'
  | 'model_plan'
  | 'tool_start'
  | 'tool_result'
  | 'model_message'
  | 'final_answer'
  | 'error';

export interface ToolCallPlanItem {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolStartEvent {
  tool_call_id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResultEvent {
  tool_call_id: string;
  name: string;
  status?: string;
  result?: any;
  error?: string;
}

export interface StreamEvent<T = any> {
  event: StreamEventType;
  data: T;
  timestamp: number;
}

export interface ToolCallStateItem {
  id: string; // tool_call_id
  name: string;
  arguments: Record<string, any>;
  status: 'pending' | 'running' | 'success' | 'error';
  result?: any;
  error?: string;
  startedAt?: number;
  finishedAt?: number;
}

// 侧边栏状态
export interface SidebarState {
  isOpen: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
}
