import React, { useEffect, useRef } from 'react';
import { Spin } from 'antd';
import MessageItem from './MessageItem';
import type { Message } from '../types';

interface ChatMessagesProps {
  messages: Message[];
  isLoading: boolean;
  onDownloadFile: (fileUrl: string, fileName: string) => Promise<void>;
  onDownloadRelatedFiles: (files: string[]) => Promise<void>;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  isLoading,
  onDownloadFile,
  onDownloadRelatedFiles,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-2xl mx-auto px-4">
          <div className="flex items-center justify-center gap-4" style={{ marginBottom: '32px' }}>
            <span className="text-4xl md:text-6xl">🗺️</span>
            <span className="text-4xl  text-gray-900">欢迎使用地理空间AI助手</span>
          </div>

          <p className="text-lg text-gray-700" style={{ marginTop: '20px', marginBottom: '32px' }}>
            我可以帮您进行地理空间数据分析，包括：
          </p>
          <div className="grid grid-cols-2 gap-6 text-lg text-gray-600 justify-items-center text-center" style={{ marginBottom: '24px' }}>
            <div className="flex items-center justify-center space-x-2">
              <span className="text-blue-500">🎯</span>
              <span>K-Means 聚类分析</span>
            </div>
            <div className="flex items-center justify-center space-x-2">
              <span className="text-red-500">🔥</span>
              <span>热力图生成</span>
            </div>
            <div className="flex items-center justify-center space-x-2">
              <span className="text-green-500">📊</span>
              <span>数据预处理筛选</span>
            </div>
            <div className="flex items-center justify-center space-x-2">
              <span className="text-purple-500">🎬</span>
              <span>GIF 动画合成</span>
            </div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
            <p className="text-lg text-blue-700 text-center" style={{ paddingLeft: '24px', paddingRight: '24px',paddingTop:'12px' }} >
              <strong>试试看 </strong>"上传文件，并告诉我你的需求"
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      <div className="mx-auto p-4 px-2 w-full max-w-5xl">
        {/* 消息列表 */}
        {messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            onDownloadFile={onDownloadFile}
            onDownloadRelatedFiles={onDownloadRelatedFiles}
          />
        ))}

        {/* 加载指示器 */}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-white text-gray-900 border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm px-4 py-3">
              <div className="flex items-center space-x-3">
                <Spin size="small" />
                <span className="text-sm text-gray-500">AI正在思考...</span>
              </div>
            </div>
          </div>
        )}

        {/* 滚动锚点 */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatMessages;
