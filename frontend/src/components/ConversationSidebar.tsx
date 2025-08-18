import React, { useState } from 'react';
import { Button, Drawer, List, Typography, Popconfirm, Avatar, Dropdown, Input } from 'antd';
import { 
  MenuOutlined, 
  PlusOutlined, 
  MessageOutlined, 
  DeleteOutlined,
  UserOutlined,
  SettingOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import type { Conversation } from '../types';

const { Text } = Typography;

interface ConversationSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  isOpen,
  onToggle,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const formatDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return '今天';
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN');
    }
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '开源用户' },
    { key: 'settings', icon: <SettingOutlined />, label: '偏好设置（仅前端）' },
    { key: 'about', icon: <InfoCircleOutlined />, label: '关于本项目' },
  ];

  const startEdit = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditingTitle(conv.title);
  };

  const confirmEdit = () => {
    if (editingId) {
      const newTitle = editingTitle.trim() || '未命名对话';
      onRenameConversation(editingId, newTitle);
      setEditingId(null);
      setEditingTitle('');
    }
  };

  const sidebarContent = (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <Text strong className="text-lg">对话记录</Text>
          {/* 移除内部关闭按钮，点击遮罩即可关闭 */}
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={onToggle}
            size="small"
            className="lg:hidden"
            title="关闭侧边栏"
          />
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onNewConversation}
          className="w-full"
        >
          新建对话
        </Button>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageOutlined className="text-2xl mb-2" />
            <p className="text-sm">暂无对话记录</p>
            <p className="text-xs mt-1">点击上方按钮开始新对话</p>
          </div>
        ) : (
          <List
            dataSource={conversations}
            renderItem={(conversation) => (
              <List.Item
                className={`group cursor-pointer transition-colors hover:bg-gray-50 border-b-0 ${
                  conversation.id === activeConversationId 
                    ? 'bg-blue-50 border-r-2 border-blue-500' 
                    : ''
                }`}
                onClick={() => onSelectConversation(conversation.id)}
                style={{ padding: '12px 16px' }}
              >
                <div className="w-full">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {editingId === conversation.id ? (
                        <Input
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onPressEnter={(e) => { e.stopPropagation(); confirmEdit(); }}
                          onBlur={(e) => { e.stopPropagation(); confirmEdit(); }}
                          autoFocus
                          size="small"
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <Text 
                          className={`block text-sm font-medium truncate ${
                            conversation.id === activeConversationId 
                              ? 'text-blue-700' 
                              : 'text-gray-900'
                          }`}
                          title={conversation.title + '（双击可重命名）'}
                          onDoubleClick={(e) => { e.stopPropagation(); startEdit(conversation); }}
                        >
                          {conversation.title}
                        </Text>
                      )}
                      <Text className="text-xs text-gray-500 mt-1">
                        {formatDate(conversation.lastActive)}
                      </Text>
                      {conversation.messages.length > 0 && (
                        <Text className="text-xs text-gray-400 block mt-1 truncate">
                          {conversation.messages.length} 条消息
                        </Text>
                      )}
                    </div>
                    <Popconfirm
                      title="确定删除这个对话吗？"
                      description="删除后无法恢复"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        onDeleteConversation(conversation.id);
                      }}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        className="opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                        onClick={(e) => e.stopPropagation()}
                        title="删除对话"
                      />
                    </Popconfirm>
                  </div>
                </div>
              </List.Item>
            )}
          />
        )}
      </div>

      {/* 底部 - 用户身份（仅前端展示） */}
      <div className="p-4 border-t border-gray-200">
        <Dropdown
          menu={{ items: userMenuItems }}
          trigger={['click']}
        >
          <div className="flex items-center cursor-pointer">
            <Avatar size={36} icon={<UserOutlined />} className="mr-2" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">开源用户</div>
              <div className="text-xs text-gray-500 truncate">srtp-example@local</div>
            </div>
          </div>
        </Dropdown>
      </div>
    </div>
  );

  return (
    <>
      {/* 移动端和小屏幕的抽屉 */}
      <Drawer
        title={null}
        placement="left"
        onClose={onToggle}
        open={isOpen}
        className="lg:hidden"
        width={300}
        bodyStyle={{ padding: 0 }}
        closable={false}
      >
        {sidebarContent}
      </Drawer>

      {/* 大屏幕的固定侧边栏 */}
      <div 
        className={`hidden lg:flex lg:flex-col lg:w-80 bg-white border-r border-gray-200 transition-all duration-300 ${
          isOpen ? 'lg:translate-x-0' : 'lg:-translate-x-full lg:w-0'
        }`}
      >
        {isOpen && sidebarContent}
      </div>

      {/* 移除左上角悬浮切换按钮，避免遮挡标题 */}
    </>
  );
};

export default ConversationSidebar;
