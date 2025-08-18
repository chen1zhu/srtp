import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { Button } from 'antd';
import { DownloadOutlined, FolderOpenOutlined } from '@ant-design/icons';
import ImagePreview from './ImagePreview';
import type { Message } from '../types';

interface MessageItemProps {
  message: Message;
  onDownloadFile: (fileUrl: string, fileName: string) => Promise<void>;
  onDownloadRelatedFiles: (files: string[]) => Promise<void>;
}

const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onDownloadFile,
  onDownloadRelatedFiles,
}) => {
  // 需求：bounds（边界文件）与 filter（过滤点数据）先不要直接渲染到页面
  // 识别规则：文件名以 bounds_/filter_/filtered_ 开头，且扩展名为 json/csv/geojson
  const isDeferredFile = (file: string) => {
    const name = (file.split('/')?.pop() || file).toLowerCase();
    const ext = name.split('.').pop() || '';
    const isTargetName = name.startsWith('bounds_') || name.startsWith('filter_') || name.startsWith('filtered_');
    const isTargetExt = ['json', 'csv', 'geojson'].includes(ext);
    return isTargetName && isTargetExt;
  };

  const generated = message.generatedFiles || [];
  const deferredFiles = generated.filter(isDeferredFile);
  const normalFiles = generated.filter(f => !isDeferredFile(f));
  const [showDeferred, setShowDeferred] = useState(false);

  return (
    <div
      className={`flex ${message.role === 'user' ? 'justify-end pr-2' : 'justify-start pl-2'} mb-3`}
    >
      <div
        className={`max-w-[85%] ${
          message.role === 'user'
            ? 'bg-blue-500 text-white rounded-2xl rounded-br-sm'
            : 'bg-white text-gray-900 border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm'
        } px-4 py-3`}
      >
        {/* 消息内容 */}
        {message.role === 'user' ? (
          <p className="text-sm whitespace-pre-wrap leading-tight" style={{ margin: 0 }}>{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              rehypePlugins={[rehypeHighlight]}
              components={{
                // 自定义样式组件
                h1: ({ node, ...props }: any) => <h1 className="text-lg font-bold mb-3 text-gray-900" {...props} />,
                h2: ({ node, ...props }: any) => <h2 className="text-base font-semibold mb-2 text-gray-800" {...props} />,
                h3: ({ node, ...props }: any) => <h3 className="text-sm font-semibold mb-2 text-gray-700" {...props} />,
                p: ({ node, ...props }: any) => <p className="mb-3 last:mb-0 leading-relaxed text-gray-700" {...props} />,
                ul: ({ node, ...props }: any) => <ul className="list-disc list-inside mb-3 space-y-1 text-gray-700" {...props} />,
                ol: ({ node, ...props }: any) => <ol className="list-decimal list-inside mb-3 space-y-1 text-gray-700" {...props} />,
                li: ({ node, ...props }: any) => <li className="text-sm leading-relaxed" {...props} />,
                code: ({ node, className, children, ...props }: any) => {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match;
                  return isInline ? (
                    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-pink-600" {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className="block bg-gray-900 text-gray-100 p-3 rounded-lg text-xs font-mono overflow-x-auto" {...props}>
                      {children}
                    </code>
                  );
                },
                pre: ({ node, ...props }: any) => <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg text-xs overflow-x-auto mb-3" {...props} />,
                blockquote: ({ node, ...props }: any) => <blockquote className="border-l-4 border-blue-300 pl-4 italic mb-3 text-gray-600" {...props} />,
                strong: ({ node, ...props }: any) => <strong className="font-semibold text-gray-900" {...props} />,
                em: ({ node, ...props }: any) => <em className="italic text-gray-700" {...props} />,
                a: ({ node, ...props }: any) => <a className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" {...props} />,
                table: ({ node, ...props }: any) => (
                  <div className="overflow-x-auto mb-3">
                    <table className="min-w-full border border-gray-300 rounded-lg" {...props} />
                  </div>
                ),
                thead: ({ node, ...props }: any) => <thead className="bg-gray-50" {...props} />,
                th: ({ node, ...props }: any) => <th className="border border-gray-300 px-3 py-2 text-xs font-semibold text-left text-gray-700" {...props} />,
                td: ({ node, ...props }: any) => <td className="border border-gray-300 px-3 py-2 text-xs text-gray-700" {...props} />,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        
        {/* 生成的文件（拆分：正常展示 vs 延迟展示：bounds/filter） */}
        {generated.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
            {/* 正常展示的文件 */}
            {normalFiles.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-gray-600 flex items-center mb-0" style={{ fontSize: '16px', marginBottom: '0px' }}>
                    <FolderOpenOutlined className="mr-2" />
                    生成的文件 ({normalFiles.length})
                  </p>
                  {normalFiles.length > 1 && (
                    <Button
                      size="small"
                      type="primary"
                      ghost
                      icon={<DownloadOutlined />}
                      onClick={() => onDownloadRelatedFiles(normalFiles)}
                      className="text-xs"
                    >
                      批量下载
                    </Button>
                  )}
                </div>
                <div className="space-y-2">
                  {normalFiles.map((file, index) => {
                    const fileName = file.split('/').pop() || file;
                    const isImage = fileName.toLowerCase().match(/\.(png|jpg|jpeg|gif|webp)$/);
                    return (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                          <a
                            href={file}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline flex-1 text-xs truncate"
                            title={fileName}
                          >
                            📁 {fileName}
                          </a>
                          <Button
                            size="small"
                            type="text"
                            icon={<DownloadOutlined />}
                            onClick={() => onDownloadFile(file, fileName)}
                            className="ml-2 text-xs"
                            title="下载文件"
                          />
                        </div>
                        {isImage && (
                          <ImagePreview
                            src={file}
                            alt={fileName}
                            fileName={fileName}
                            className="mt-2"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 延迟展示的 bounds/filter 文件 */}
            {deferredFiles.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-amber-700 mb-0">
                    检测到 {deferredFiles.length} 个边界/过滤数据文件（bounds/filter），为避免大数据量影响体验，未自动展示。
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      size="small"
                      onClick={() => setShowDeferred(v => !v)}
                      className="text-xs"
                    >
                      {showDeferred ? '收起' : '展开查看'}
                    </Button>
                    <Button
                      size="small"
                      type="primary"
                      ghost
                      icon={<DownloadOutlined />}
                      onClick={() => onDownloadRelatedFiles(deferredFiles)}
                      className="text-xs"
                    >
                      批量下载
                    </Button>
                  </div>
                </div>
                {showDeferred && (
                  <div className="mt-3 space-y-2">
                    {deferredFiles.map((file, index) => {
                      const fileName = file.split('/').pop() || file;
                      return (
                        <div key={index} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-amber-200">
                          <span className="text-amber-700 flex-1 text-xs truncate" title={fileName}>📁 {fileName}</span>
                          <Button
                            size="small"
                            type="text"
                            icon={<DownloadOutlined />}
                            onClick={() => onDownloadFile(file, fileName)}
                            className="ml-2 text-xs"
                            title="下载文件"
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* 时间戳 */}
        <p className={`text-xs mt-1 ${
          message.role === 'user' ? 'text-blue-100' : 'text-gray-400'
        }`} style={{ margin: '4px 0 0 0' }}>
          {message.timestamp.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </p>
      </div>
    </div>
  );
};

export default MessageItem;
