import { useState } from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import ConversationSidebar from './components/ConversationSidebar';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import { useConversations } from './hooks/useConversations';
import type { Message, ChatResponse } from './types';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [requiresFollowUp, setRequiresFollowUp] = useState(false);

  const {
    conversations,
    activeConversation,
    activeConversationId,
    createNewConversation,
    addMessageToConversation,
    updateConversationMeta,
    deleteConversation,
    switchToConversation,
    getConversationById,
  } = useConversations();

  const addMessage = (content: string, role: 'user' | 'assistant', generatedFiles?: string[]) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(2, 11),
      content,
      role,
      timestamp: new Date(),
      generatedFiles
    };

    let conversationId = activeConversationId;
    if (!conversationId) {
      conversationId = createNewConversation();
    }

    addMessageToConversation(conversationId, newMessage, role === 'user');
    return conversationId; // 返回用于此次消息的会话ID
  };

  const handleSend = async () => {
    if ((!input.trim() && !selectedFile) || isLoading) return;

    const userMessage = selectedFile ? `${input} [文件: ${selectedFile.name}]` : input.trim();
    const convIdForThisSend = addMessage(userMessage, 'user');
    setInput('');
    setIsLoading(true);

    try {
      let url: string;
      let requestBody: FormData | string;
      let headers: Record<string, string>;

      const activeConv = getConversationById(convIdForThisSend);

      // 判断是开始新对话还是继续对话（用serverId而不是本地id）
      if (!activeConv || !activeConv.serverId) {
        url = 'http://localhost:8000/chat/start';
      } else {
        url = `http://localhost:8000/chat/continue/${activeConv.serverId}`;
      }

      // 如果有文件，使用 FormData
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('query', input.trim() || '请分析这个文件');
        requestBody = formData;
        headers = {
          'Accept': 'application/json',
        };
      } else {
        // 只有文本消息
        requestBody = JSON.stringify({ query: input.trim() });
        headers = {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        };
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        mode: 'cors',
        body: requestBody,
      });

      if (response.ok) {
        const data: ChatResponse = await response.json();
        
        // 保存serverId到当前对话
        updateConversationMeta(convIdForThisSend, { serverId: data.conversation_id, requiresFollowUp: data.requires_follow_up });
        setRequiresFollowUp(data.requires_follow_up);
        
        // 添加AI回复消息
        addMessage(data.answer, 'assistant', data.generated_files);
        
        // 清除选中的文件
        setSelectedFile(null);
      } else if (response.status === 404) {
        addMessage('对话已过期或不存在，请重新开始对话。', 'assistant');
        // 重置对话状态
        setRequiresFollowUp(false);
        handleNewConversation();
      } else if (response.status === 405) {
        addMessage('请求方法不被允许，可能是后端 CORS 配置问题。', 'assistant');
      } else {
        const errorText = await response.text();
        addMessage(`服务器错误 (${response.status}): ${errorText}`, 'assistant');
      }
    } catch (error) {
      console.error('Network error:', error);
      addMessage('网络连接错误，请检查后端服务是否启动。', 'assistant');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    const newId = createNewConversation();
    setRequiresFollowUp(false);
    setSelectedFile(null);
    setInput('');
    return newId;
  };

  // 下载单个文件
  const downloadFile = async (fileUrl: string, fileName: string) => {
    try {
      const response = await fetch(fileUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下载文件失败:', error);
    }
  };

  // 批量下载相关文件（主要针对shp文件）
  const downloadRelatedFiles = async (files: string[]) => {
    // 找出所有shp相关文件
    const shpFiles = files.filter(file => {
      const fileName = file.split('/').pop() || file;
      return fileName.toLowerCase().match(/\.(shp|shx|dbf|prj|cpg)$/);
    });
    
    if (shpFiles.length > 0) {
      // 获取基础文件名（不含扩展名）
      const baseNames = new Set(
        shpFiles.map(file => {
          const fileName = file.split('/').pop() || file;
          return fileName.replace(/\.(shp|shx|dbf|prj|cpg)$/i, '');
        })
      );
      
      // 为每个基础名称下载所有相关文件
      for (const baseName of baseNames) {
        const relatedFiles = shpFiles.filter(file => {
          const fileName = file.split('/').pop() || file;
          return fileName.toLowerCase().startsWith(baseName.toLowerCase());
        });
        
        // 逐个下载相关文件
        for (const file of relatedFiles) {
          const fileName = file.split('/').pop() || file;
          await downloadFile(file, fileName);
          // 添加小延迟避免浏览器限制
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
    } else {
      // 如果没有shp文件，就下载所有文件
      for (const file of files) {
        const fileName = file.split('/').pop() || file;
        await downloadFile(file, fileName);
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
  };

  return (
    <ConfigProvider locale={zhCN} theme={{
      token: {
        colorBgLayout: '#a99572ff',
        colorBgContainer: '#e7eaebff',
        colorBorder: '#ea6636ff',
        borderRadiusLG: 12,
      },
    }}>
      <div className="h-screen flex">
        {/* 侧边栏 */}
        <ConversationSidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={switchToConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={deleteConversation}
          onRenameConversation={(id: string, title: string) => updateConversationMeta(id, { title })}
        />

        {/* 主聊天区域 */}
        <div className={`flex-1 flex flex-col transition-all duration-300${
          isSidebarOpen ? 'lg:ml-0' : ''
        }`}>
          {/* 头部 */}
          <div className="bg-white border-b border-gray-200 px-4 py-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {/* 菜单按钮放在标题左侧，避免覆盖 */}
                <button
                  aria-label="打开对话列表"
                  className="p-2 rounded hover:bg-gray-100 border"
                  onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                >
                  ☰
                </button>
                {/* 标题与当前对话名称同一行显示 */}
                <div className="flex items-center space-x-3 min-w-0">
                  <h1
                    className="text-lg font-semibold text-gray-900 whitespace-nowrap m-0"
                    style={{ lineHeight: 1, transform:'translateY(3.5px)' }}
                  >
                    AI 地理空间数据分析助手
                  </h1>
                  <span
                    className="text-md text-gray-600 truncate max-w-xs lg:max-w-2xl"
                    style={{ lineHeight: 1 }}
                  >
                    {activeConversation?.title || '新对话'}
                  </span>
                </div>
              </div>
              {activeConversationId && requiresFollowUp && (
                <div className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-xs font-medium">
                  等待补充信息
                </div>
              )}
            </div>
          </div>

          {/* 消息区域 */}
          <ChatMessages
            messages={activeConversation?.messages || []}
            isLoading={isLoading}
            onDownloadFile={downloadFile}
            onDownloadRelatedFiles={downloadRelatedFiles}
          />

          {/* 输入区域 */}
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={handleSend}
            isLoading={isLoading}
            selectedFile={selectedFile}
            setSelectedFile={setSelectedFile}
            requiresFollowUp={requiresFollowUp}
          />
        </div>
      </div>
    </ConfigProvider>
  );
}

export default App;
