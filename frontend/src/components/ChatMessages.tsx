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
      <div className="flex-1 flex items-center justify-center px-4" style={{ background: 'radial-gradient(circle at top, rgba(255,255,255,0.88) 0%, rgba(244,247,251,0.94) 45%, rgba(239,243,248,1) 100%)' }}>
        <div
          className="w-full max-w-2xl text-center"
          style={{
            border: '1px solid rgba(255,255,255,0.72)',
            borderRadius: '28px',
            padding: '36px 28px',
            background: 'linear-gradient(180deg, rgba(255,255,255,0.84) 0%, rgba(255,255,255,0.72) 100%)',
            boxShadow: '0 24px 60px rgba(15,23,42,0.08)',
            backdropFilter: 'blur(16px)',
          }}
        >
          <div className="flex justify-center" style={{ marginBottom: '20px' }}>
            <div
              aria-hidden="true"
              style={{
                width: '96px',
                height: '64px',
                borderRadius: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(148,163,184,0.24)',
                background: 'linear-gradient(135deg, rgba(59,130,246,0.16) 0%, rgba(14,165,233,0.08) 100%)',
                color: '#1d4ed8',
                fontSize: '1.25rem',
                fontWeight: 800,
                letterSpacing: '0.08em',
                boxShadow: '0 14px 32px rgba(37,99,235,0.12)',
              }}
            >
              GeoAI
            </div>
          </div>

          <p className="text-xs font-semibold text-blue-700" style={{ letterSpacing: '0.22em', marginBottom: '12px' }}>
            
          </p>

          <h2
            className="text-2xl md:text-4xl text-gray-900"
            style={{
              fontWeight: 800,
              fontFamily: 'Manrope, Noto Sans SC, sans-serif',
              letterSpacing: '-0.03em',
              marginBottom: '14px',
            }}
          >
            
          </h2>

          <p
            className="text-base md:text-lg text-gray-600 mx-auto"
            style={{
              maxWidth: '38rem',
              lineHeight: 1.8,
              marginBottom: '22px',
            }}
          >
            描述你的分析目标，或上传数据文件后继续分析。
          </p>

          <div
            className="inline-flex items-center justify-center rounded-full border border-gray-200 bg-white px-5 py-2 text-sm text-gray-600"
            style={{ boxShadow: '0 10px 24px rgba(33, 59, 119, 0.05)' }}
          >
            例如：请对表格中的出租车轨迹点进行聚类并输出可视化结果
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: 'linear-gradient(180deg, rgba(248,250,252,0.92) 0%, rgba(241,245,249,0.98) 100%)' }}>
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
            <div className="bg-white text-gray-900 border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm px-4 py-3" style={{ boxShadow: '0 10px 24px rgba(15,23,42,0.06)' }}>
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
