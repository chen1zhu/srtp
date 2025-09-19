import { useState, useRef, useEffect } from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import ConversationSidebar from './components/ConversationSidebar';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import { useConversations } from './hooks/useConversations';
import type { ChatResponse, StreamEvent, ToolCallStateItem } from './types';
import ToolCallPanel from './components/ToolCallPanel';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [requiresFollowUp, setRequiresFollowUp] = useState(false);
  // 流式相关状态
  const [useStream, setUseStream] = useState(true); // 可后续做成设置项
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallStateItem[]>([]);
  const eventBufferRef = useRef('');
  // 记录当前轮是否已经插入过工具调用快照，避免重复
  const toolSnapshotInsertedRef = useRef(false);
  // 追踪最新 toolCalls 的 ref，供事件回调使用
  const toolCallsRef = useRef<ToolCallStateItem[]>([]);
  useEffect(() => { toolCallsRef.current = toolCalls; }, [toolCalls]);

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

  const resetStreamingState = () => {
    setStreamEvents([]);
    setToolCalls([]);
    eventBufferRef.current = '';
  toolSnapshotInsertedRef.current = false;
  };

  const handleSend = async () => {
    if ((!input.trim() && !selectedFile) || isLoading) return;

    const userMessage = selectedFile ? `${input} [文件: ${selectedFile.name}]` : input.trim();
    
    // 先确定要使用的对话ID
    let convIdForThisSend = activeConversationId;
    if (!convIdForThisSend) {
      convIdForThisSend = createNewConversation();
    }
    
    // 添加用户消息到确定的对话中
    addMessageToConversation(convIdForThisSend, {
      id: crypto.randomUUID(),
      content: userMessage,
      role: 'user' as const,
      timestamp: new Date(),
      generatedFiles: []
    }, true);
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

      if (useStream) {
        resetStreamingState();
        // 替换为流式端点
        const streamUrl = (!activeConv || !activeConv.serverId)
          ? 'http://localhost:8000/chat/stream/start'
          : `http://localhost:8000/chat/stream/continue/${activeConv.serverId}`;
        const response = await fetch(streamUrl, {
          method: 'POST',
            headers,
            mode: 'cors',
            body: requestBody,
        });
  if (!response.ok || !response.body) {
          // 回退到普通模式
          addMessageToConversation(convIdForThisSend, {
            id: crypto.randomUUID(),
            content: '无法建立流式连接，已回退为普通请求。',
            role: 'assistant',
            timestamp: new Date(),
            generatedFiles: []
          }, false);
          setUseStream(false);
        } else {
          const serverConvId = response.headers.get('X-Conversation-ID');
          if (serverConvId && (!activeConv || !activeConv.serverId)) {
            updateConversationMeta(convIdForThisSend, { serverId: serverConvId });
          }
          const reader = response.body.getReader();
          const decoder = new TextDecoder('utf-8');
          let done = false;
          while (!done) {
            const { value, done: readerDone } = await reader.read();
            if (value) {
              const chunk = decoder.decode(value, { stream: true });
              eventBufferRef.current += chunk;
              const parts = eventBufferRef.current.split('\n\n');
              for (let i = 0; i < parts.length - 1; i++) {
                const block = parts[i].trim();
                if (!block) continue;
                const lines = block.split('\n');
                let eventType: string | null = null;
                let dataLine = '';
                for (const line of lines) {
                  if (line.startsWith('event: ')) eventType = line.substring(7).trim();
                  if (line.startsWith('data: ')) dataLine += line.substring(6).trim();
                }
                if (eventType) {
                  try {
                    const dataObj = JSON.parse(dataLine);
                    const ev: StreamEvent = { event: eventType as any, data: dataObj, timestamp: Date.now() };
                    setStreamEvents(prev => [...prev, ev]);
                    // 状态机
                    if (ev.event === 'model_plan') {
                      const plan = (dataObj.tool_calls || []) as any[];
                      setToolCalls(plan.map(p => ({ id: p.id, name: p.name, arguments: p.arguments || {}, status: 'pending' })));
                    } else if (ev.event === 'tool_start') {
                      setToolCalls(prev => prev.map(c => c.id === dataObj.tool_call_id ? { ...c, status: 'running', startedAt: Date.now() } : c));
                    } else if (ev.event === 'tool_result') {
                      setToolCalls(prev => prev.map(c => c.id === dataObj.tool_call_id ? { ...c, status: dataObj.error ? 'error' : 'success', result: dataObj.result, error: dataObj.error, finishedAt: Date.now() } : c));
                    } else if (ev.event === 'final_answer') {
                      // 仅首次插入工具调用快照
                      if (!toolSnapshotInsertedRef.current && toolCallsRef.current.length > 0) {
                        const snapshot = toolCallsRef.current.map(c => ({
                          id: c.id,
                          name: c.name,
                          status: c.status,
                          arguments: c.arguments,
                          result: c.result,
                          error: c.error,
                          startedAt: c.startedAt,
                          finishedAt: c.finishedAt,
                        }));
                        addMessageToConversation(convIdForThisSend, {
                          id: crypto.randomUUID(),
                          role: 'tool_calls',
                          timestamp: new Date(),
                          content: JSON.stringify({ toolCalls: snapshot, finalAnswerPreview: dataObj.content?.slice(0,120) || '' })
                        }, false);
                        toolSnapshotInsertedRef.current = true;
                      }
                      // 最终回答落入消息
                      updateConversationMeta(convIdForThisSend, { requiresFollowUp: dataObj.requires_follow_up });
                      setRequiresFollowUp(dataObj.requires_follow_up);
                      addMessageToConversation(convIdForThisSend, {
                        id: crypto.randomUUID(),
                        content: dataObj.content,
                        role: 'assistant',
                        timestamp: new Date(),
                        generatedFiles: (dataObj.generated_files || []).map((f: string) => `http://localhost:8000/outputs/${f}`)
                      }, false);
                      setSelectedFile(null);
                    }
                  } catch (e) {
                    // ignore
                  }
                }
              }
              eventBufferRef.current = parts[parts.length - 1];
            }
            done = readerDone;
          }
        }
      } else {
        const response = await fetch(url, {
          method: 'POST',
          headers,
          mode: 'cors',
          body: requestBody,
        });
        if (response.ok) {
          const data: ChatResponse = await response.json();
          updateConversationMeta(convIdForThisSend, { serverId: data.conversation_id, requiresFollowUp: data.requires_follow_up });
          setRequiresFollowUp(data.requires_follow_up);
          addMessageToConversation(convIdForThisSend, {
            id: crypto.randomUUID(),
            content: data.answer,
            role: 'assistant',
            timestamp: new Date(),
            generatedFiles: data.generated_files || []
          }, false);
          setSelectedFile(null);
        } else if (response.status === 404) {
          addMessageToConversation(convIdForThisSend, { id: crypto.randomUUID(), content: '对话已过期或不存在，请重新开始对话。', role: 'assistant', timestamp: new Date(), generatedFiles: [] }, false);
          setRequiresFollowUp(false);
          handleNewConversation();
        } else if (response.status === 405) {
          addMessageToConversation(convIdForThisSend, { id: crypto.randomUUID(), content: '请求方法不被允许，可能是后端 CORS 配置问题。', role: 'assistant', timestamp: new Date(), generatedFiles: [] }, false);
        } else {
          const errorText = await response.text();
          addMessageToConversation(convIdForThisSend, { id: crypto.randomUUID(), content: `服务器错误 (${response.status}): ${errorText}`, role: 'assistant', timestamp: new Date(), generatedFiles: [] }, false);
        }
      }
    } catch (error) {
      console.error('Network error:', error);
      addMessageToConversation(convIdForThisSend, {
        id: crypto.randomUUID(),
        content: '网络连接错误，请检查后端服务是否启动。',
        role: 'assistant' as const,
        timestamp: new Date(),
        generatedFiles: []
      }, false);
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

          {/* 工具调用链显示区域（在消息列表上方） */}
          { (toolCalls.length > 0 || streamEvents.length > 0 || (isLoading && useStream)) && (
            <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
              <ToolCallPanel
                events={streamEvents}
                toolCalls={toolCalls}
                isStreaming={isLoading}
              />
            </div>
          )}

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
          {/* 可选：底部显示是否流式模式的切换（简单占位） */}
          <div className="text-[10px] text-gray-400 text-center pb-1 select-none">模式: {useStream ? '流式' : '普通'}（可在代码中修改 useStream）</div>
        </div>
      </div>
    </ConfigProvider>
  );
}

export default App;
