import { useState, useCallback, useEffect } from 'react';
import type { Message, Conversation } from '../types';

export const useConversations = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // 从localStorage加载对话记录
  useEffect(() => {
    const saved = localStorage.getItem('ai-chat-conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // 转换日期字符串回Date对象
        const restored = parsed.map((conv: any) => ({
          ...conv,
          lastActive: new Date(conv.lastActive),
          messages: conv.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        setConversations(restored);
      } catch (error) {
        console.error('Failed to load conversations:', error);
      }
    }
  }, []);

  // 保存对话记录到localStorage
  const saveConversations = useCallback((convs: Conversation[]) => {
    try {
      localStorage.setItem('ai-chat-conversations', JSON.stringify(convs));
    } catch (error) {
      console.error('Failed to save conversations:', error);
    }
  }, []);

  // 创建新对话
  const createNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: `conv_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      title: '新对话',
      messages: [],
      lastActive: new Date()
    };
    
    const updated = [newConv, ...conversations];
    setConversations(updated);
    setActiveConversationId(newConv.id);
    saveConversations(updated);
    
    return newConv.id;
  }, [conversations, saveConversations]);

  // 添加消息到对话
  const addMessageToConversation = useCallback((
    conversationId: string, 
    message: Message,
    updateTitle?: boolean
  ) => {
    setConversations(prev => {
      const updated = prev.map(conv => {
        if (conv.id === conversationId) {
          const updatedConv: Conversation = {
            ...conv,
            messages: [...conv.messages, message],
            lastActive: new Date()
          };
          
          // 如果是第一条用户消息，更新标题
          if (updateTitle && conv.messages.length === 0 && message.role === 'user') {
            updatedConv.title = message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '');
          }
          
          return updatedConv;
        }
        return conv;
      });
      
      saveConversations(updated);
      return updated;
    });
  }, [saveConversations]);

  // 更新对话元数据（serverId、requiresFollowUp、title等）
  const updateConversationMeta = useCallback((
    conversationId: string,
    meta: Partial<Pick<Conversation, 'serverId' | 'requiresFollowUp' | 'title'>>
  ) => {
    setConversations(prev => {
      const updated = prev.map(conv => conv.id === conversationId ? { ...conv, ...meta } : conv);
      saveConversations(updated);
      return updated;
    });
  }, [saveConversations]);

  // 删除对话
  const deleteConversation = useCallback((conversationId: string) => {
    setConversations(prev => {
      const updated = prev.filter(conv => conv.id !== conversationId);
      saveConversations(updated);
      
      // 如果删除的是当前激活的对话，切换到第一个对话
      if (conversationId === activeConversationId) {
        setActiveConversationId(updated.length > 0 ? updated[0].id : null);
      }
      
      return updated;
    });
  }, [activeConversationId, saveConversations]);

  // 获取当前激活的对话
  const activeConversation = conversations.find(conv => conv.id === activeConversationId);

  // 切换对话
  const switchToConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
  }, []);

  // 获取对话
  const getConversationById = useCallback((conversationId: string) => {
    return conversations.find(c => c.id === conversationId);
  }, [conversations]);

  return {
    conversations,
    activeConversation,
    activeConversationId,
    createNewConversation,
    addMessageToConversation,
    updateConversationMeta,
    deleteConversation,
    switchToConversation,
    getConversationById,
  };
};
