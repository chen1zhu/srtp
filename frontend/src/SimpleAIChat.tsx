import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import { Button, Upload } from 'antd';
import { UploadOutlined, SendOutlined } from '@ant-design/icons';
import 'antd/dist/reset.css';

// 类型定义
interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  generatedFiles?: string[];
}

interface ChatResponse {
  conversation_id: string;
  answer: string;
  requires_follow_up: boolean;
  generated_files: string[];
}

// AI聊天应用
function SimpleAIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [requiresFollowUp, setRequiresFollowUp] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const addMessage = (content: string, role: 'user' | 'assistant', generatedFiles?: string[]) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(2, 11),
      content,
      role,
      timestamp: new Date(),
      generatedFiles
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setInput('');
  };

  const handleSend = async () => {
    if ((!input.trim() && !selectedFile) || isLoading) return;

    const userMessage = selectedFile ? `${input} [文件: ${selectedFile.name}]` : input.trim();
    setInput('');
    addMessage(userMessage, 'user');
    setIsLoading(true);

    try {
      let url: string;
      let requestBody: FormData | string;
      let headers: Record<string, string>;

      // 判断是开始新对话还是继续对话
      if (!conversationId) {
        // 开始新对话
        url = 'http://localhost:8000/chat/start';
      } else {
        // 继续对话
        url = `http://localhost:8000/chat/continue/${conversationId}`;
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
        
        // 更新对话状态
        setConversationId(data.conversation_id);
        setRequiresFollowUp(data.requires_follow_up);
        
        // 添加AI回复消息
        addMessage(data.answer, 'assistant', data.generated_files);
        
        // 清除选中的文件
        setSelectedFile(null);
      } else if (response.status === 404) {
        addMessage('对话已过期或不存在，请重新开始对话。', 'assistant');
        // 重置对话状态
        setConversationId(null);
        setRequiresFollowUp(false);
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startNewConversation = () => {
    setConversationId(null);
    setRequiresFollowUp(false);
    setMessages([]);
    setSelectedFile(null);
    setInput('');
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
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 头部 */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0 pr-4">
            <h1 className="text-xl font-semibold text-gray-900">AI 地理空间数据分析助手</h1>
            <p className="text-sm text-gray-600">与AI助手对话，进行地理空间数据分析</p>
          </div>
          {conversationId && (
            <Button 
              type="primary" 
              size="large"
              onClick={startNewConversation}
              style={{ flexShrink: 0 }}
            >
              开启新对话
            </Button>
          )}
        </div>
        {conversationId && (
          <div className="mt-2 text-xs text-gray-500">
            对话ID: {conversationId.substring(0, 8)}...
            {requiresFollowUp && <span className="ml-2 text-orange-600">等待您的补充信息</span>}
          </div>
        )}
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <div className="text-4xl mb-4">🗺️</div>
            <h3 className="text-lg font-medium mb-2">欢迎使用地理空间AI助手</h3>
            <p className="mb-4">我可以帮您进行地理空间数据分析，包括：</p>
            <div className="text-sm space-y-1">
              <p>• K-Means 聚类分析</p>
              <p>• 热力图生成</p>
              <p>• 数据预处理和筛选</p>
              <p>• GIF 动画合成</p>
            </div>
            <p className="mt-4 text-xs">试试说："请帮我分析 SRTP/20200101_binjiang_point.xlsx 文件"</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white max-w-xs lg:max-w-md'
                    : 'bg-white text-gray-900 border border-gray-200 max-w-md lg:max-w-2xl'
                }`}
              >
                {message.role === 'user' ? (
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                ) : (
                  <div className="text-sm prose prose-sm max-w-none">
                    <ReactMarkdown
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        // 自定义样式组件
                        h1: ({node, ...props}: any) => <h1 className="text-lg font-bold mb-2" {...props} />,
                        h2: ({node, ...props}: any) => <h2 className="text-base font-semibold mb-2" {...props} />,
                        h3: ({node, ...props}: any) => <h3 className="text-sm font-semibold mb-1" {...props} />,
                        p: ({node, ...props}: any) => <p className="mb-2 last:mb-0" {...props} />,
                        ul: ({node, ...props}: any) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
                        ol: ({node, ...props}: any) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
                        li: ({node, ...props}: any) => <li className="text-sm" {...props} />,
                        code: ({node, className, children, ...props}: any) => {
                          const match = /language-(\w+)/.exec(className || '');
                          const isInline = !match;
                          return isInline ? (
                            <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono" {...props}>
                              {children}
                            </code>
                          ) : (
                            <code className="block bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto" {...props}>
                              {children}
                            </code>
                          );
                        },
                        pre: ({node, ...props}: any) => <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto mb-2" {...props} />,
                        blockquote: ({node, ...props}: any) => <blockquote className="border-l-4 border-gray-300 pl-3 italic mb-2" {...props} />,
                        strong: ({node, ...props}: any) => <strong className="font-semibold" {...props} />,
                        em: ({node, ...props}: any) => <em className="italic" {...props} />,
                        a: ({node, ...props}: any) => <a className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" {...props} />,
                        table: ({node, ...props}: any) => <table className="min-w-full border border-gray-300 mb-2" {...props} />,
                        thead: ({node, ...props}: any) => <thead className="bg-gray-50" {...props} />,
                        th: ({node, ...props}: any) => <th className="border border-gray-300 px-2 py-1 text-xs font-semibold text-left" {...props} />,
                        td: ({node, ...props}: any) => <td className="border border-gray-300 px-2 py-1 text-xs" {...props} />,
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}
                
                {/* 显示生成的文件 */}
                {message.generatedFiles && message.generatedFiles.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-gray-600">生成的文件:</p>
                      {message.generatedFiles.length > 1 && (
                        <button
                          onClick={() => downloadRelatedFiles(message.generatedFiles!)}
                          className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 transition-colors"
                          title="一键下载所有文件"
                        >
                          📦 打包下载
                        </button>
                      )}
                    </div>
                    <div className="space-y-1">
                      {message.generatedFiles.map((file, index) => {
                        const fileName = file.split('/').pop() || file;
                        const isImage = fileName.toLowerCase().match(/\.(png|jpg|jpeg|gif)$/);
                        return (
                          <div key={index} className="text-xs">
                            <div className="flex items-center justify-between">
                              <a 
                                href={file} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 underline flex-1"
                              >
                                📁 {fileName}
                              </a>
                              <button
                                onClick={() => downloadFile(file, fileName)}
                                className="ml-2 text-xs bg-gray-100 text-gray-700 px-1 py-0.5 rounded hover:bg-gray-200 transition-colors"
                                title="下载此文件"
                              >
                                ⬇️
                              </button>
                            </div>
                            {isImage && (
                              <div className="mt-1">
                                <img 
                                  src={file} 
                                  alt={fileName}
                                  className="max-w-full h-auto rounded border"
                                  style={{ maxHeight: '200px' }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                <p className="text-xs mt-1 opacity-70">
                  {message.timestamp.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
            </div>
          ))
        )}

        {/* 加载指示器 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-900 border border-gray-200 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-sm text-gray-500">AI正在分析...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="bg-white border-t border-gray-200 p-4">
        {/* 文件选择区域 */}
        {selectedFile && (
          <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-blue-700">📎 已选择文件:</span>
                <span className="text-sm font-medium text-blue-800">{selectedFile.name}</span>
                <span className="text-xs text-blue-600">({Math.round(selectedFile.size / 1024)} KB)</span>
              </div>
              <button
                onClick={handleRemoveFile}
                className="text-blue-600 hover:text-blue-800 text-sm"
                title="移除文件"
              >
                ✕
              </button>
            </div>
          </div>
        )}
        
        <div className="flex space-x-2">
          {/* 文件上传按钮 */}
          <Upload
            accept=".xlsx,.xls,.csv"
            beforeUpload={(file) => {
              setSelectedFile(file);
              setInput(`已选择文件: ${file.name}`);
              return false; // 阻止自动上传
            }}
            showUploadList={false}
            disabled={isLoading}
          >
            <Button icon={<UploadOutlined />} disabled={isLoading}>
              选择文件
            </Button>
          </Upload>
          
          {/* 文本输入框 */}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={
              selectedFile
                ? "为文件添加分析需求描述... (Enter发送)"
                : requiresFollowUp 
                  ? "请提供AI要求的补充信息..." 
                  : "输入您的分析需求... (Enter发送)"
            }
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus-ring"
            disabled={isLoading}
          />
          
          {/* 发送按钮 */}
          <Button
            type="primary"
            onClick={handleSend}
            disabled={isLoading || (!input.trim() && !selectedFile)}
            icon={<SendOutlined />}
          >
            发送
          </Button>
        </div>
        
        <div className="mt-2 text-xs text-gray-500">
          <p>💡 提示: 您可以上传Excel文件(.xlsx, .xls)或CSV文件进行数据分析，也可以直接对话</p>
        </div>
      </div>
    </div>
  );
}

export default SimpleAIChat;
