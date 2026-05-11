import React, { useContext, useRef, useState } from 'react';
import { Button, Drawer, List, Typography, Popconfirm, Avatar, Input, Modal, Form, Divider, Space, message as antdMessage } from 'antd';
import { 
  MenuOutlined, 
  PlusOutlined, 
  MessageOutlined, 
  DeleteOutlined,
  UserOutlined,
  LogoutOutlined,
  LockOutlined,
  CameraOutlined
} from '@ant-design/icons';
import type { Conversation } from '../types';
import { API_BASE_URL, AuthContext } from '../context/AuthContext';

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
  const { user, logout, updateAvatar, changePassword } = useContext(AuthContext);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [profileVisible, setProfileVisible] = useState(false);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordForm] = Form.useForm();
  const avatarInputRef = useRef<HTMLInputElement>(null);

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

  const avatarSrc = user?.avatar_url ? `${API_BASE_URL}${user.avatar_url}` : undefined;

  const handleAvatarSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setAvatarBusy(true);
    try {
      await updateAvatar(file);
      antdMessage.success('头像已更新');
    } catch (error: any) {
      antdMessage.error(error?.message || '头像上传失败');
    } finally {
      setAvatarBusy(false);
      event.target.value = '';
    }
  };

  const handlePasswordFinish = async (values: { current_password: string; new_password: string; confirm_password: string }) => {
    setPasswordBusy(true);
    try {
      await changePassword(values.current_password, values.new_password);
      passwordForm.resetFields();
      antdMessage.success('密码已修改');
    } catch (error: any) {
      antdMessage.error(error?.message || '修改密码失败');
    } finally {
      setPasswordBusy(false);
    }
  };

  const sidebarContent = (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%)' }}>
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200" style={{ background: 'rgba(255,255,255,0.82)', backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <Text strong className="text-lg" style={{ color: '#0f172a' }}>对话记录</Text>
            <div className="text-xs text-gray-500 mt-1">保留历史会话与当前工作流</div>
          </div>
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
          style={{ boxShadow: '0 12px 24px rgba(31,111,235,0.16)' }}
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
                style={{ padding: '12px 16px', borderRadius: 12, margin: '4px 8px' }}
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

      {/* 底部 - 用户身份 */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setProfileVisible(true)}
            className="flex flex-1 items-center text-left cursor-pointer"
            style={{ background: '#f8fafc', borderRadius: 16, padding: '10px 12px', border: '1px solid #e5ecf6' }}
          >
            <Avatar size={36} src={avatarSrc} icon={<UserOutlined />} className="mr-2" style={{ backgroundColor: '#1f6feb' }} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">{user?.full_name || user?.username || '未登录用户'}</div>
              <div className="text-xs text-gray-500 truncate">{user?.email || '未设置邮箱'}</div>
            </div>
          </button>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={logout}
            title="退出登录"
            style={{ color: '#64748b' }}
          />
        </div>
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

      <Modal
        title="个人资料"
        open={profileVisible}
        onCancel={() => setProfileVisible(false)}
        footer={null}
        destroyOnClose
      >
        <div className="flex items-center gap-4" style={{ marginBottom: 20 }}>
          <Avatar size={72} src={avatarSrc} icon={<UserOutlined />} style={{ backgroundColor: '#1f6feb' }} />
          <div className="min-w-0 flex-1">
            <div className="text-base font-semibold text-slate-900 truncate">{user?.full_name || user?.username}</div>
            <div className="text-sm text-slate-500 truncate">{user?.email}</div>
            <Space style={{ marginTop: 12 }}>
              <Button
                icon={<CameraOutlined />}
                loading={avatarBusy}
                onClick={() => avatarInputRef.current?.click()}
              >
                上传头像
              </Button>
              <Button onClick={() => passwordForm.resetFields()}>清空密码表单</Button>
            </Space>
          </div>
        </div>

        <input ref={avatarInputRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={handleAvatarSelected} />

        <Divider style={{ margin: '16px 0' }} />

        <Form form={passwordForm} layout="vertical" onFinish={handlePasswordFinish}>
          <Form.Item
            name="current_password"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码至少 8 位' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的新密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={passwordBusy} block>
            修改密码
          </Button>
        </Form>
      </Modal>

      {/* 移除左上角悬浮切换按钮，避免遮挡标题 */}
    </>
  );
};

export default ConversationSidebar;
