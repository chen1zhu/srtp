import React, { useRef, useEffect } from 'react';
import { Button, Upload, Input, Tooltip } from 'antd';
import { 
  SendOutlined, 
  UploadOutlined, 
  PaperClipOutlined,
  CloseOutlined 
} from '@ant-design/icons';

const { TextArea } = Input;

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  requiresFollowUp: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSend,
  isLoading,
  selectedFile,
  setSelectedFile,
  requiresFollowUp,
}) => {
  const textAreaRef = useRef<any>(null);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && (input.trim() || selectedFile)) {
        onSend();
      }
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
  };

  // 自适应高度但限制最大高度，超出后滚动
  useEffect(() => {
    const textArea = textAreaRef.current?.resizableTextArea?.textArea as HTMLTextAreaElement | undefined;
    if (textArea) {
      textArea.style.height = 'auto';
      const max = 160; // 上限高度
      textArea.style.maxHeight = `${max}px`;
      textArea.style.overflowY = textArea.scrollHeight > max ? 'auto' : 'hidden';
      textArea.style.height = Math.min(textArea.scrollHeight, max) + 'px';
    }
  }, [input]);

  const placeholderText = selectedFile
    ? '为文件添加分析需求描述...'
    : requiresFollowUp 
      ? '请提供AI要求的补充信息...'
      : '输入您的分析需求...';

  return (
    <div className="bg-white border-t border-gray-200" style={{ boxShadow: '0 -8px 24px rgba(15,23,42,0.04)' }}>
      {/* 文件选择区域 */}
      {selectedFile && (
        <div className="p-4 pb-0">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <PaperClipOutlined className="text-blue-600" />
                <span className="text-sm text-blue-700">已选择文件:</span>
                <span className="text-sm font-medium text-blue-800">{selectedFile.name}</span>
                <span className="text-xs text-blue-600">
                  ({(selectedFile.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={handleRemoveFile}
                className="text-blue-600 hover:text-blue-800"
                title="移除文件"
              />
            </div>
          </div>
        </div>
      )}
      
      <div className="p-4">
        <div className="flex space-x-2" style={{ alignItems: 'stretch' }}>
          {/* 文件上传按钮 */}
          <Upload
            accept=".xlsx,.xls,.csv"
            beforeUpload={(file) => {
              setSelectedFile(file);
              return false; // 阻止自动上传
            }}
            showUploadList={false}
            disabled={isLoading}
          >
            <Tooltip title="上传Excel或CSV文件">
              <Button 
                icon={<UploadOutlined />} 
                disabled={isLoading}
                size="large"
                style={{ borderRadius: 12 }}
              />
            </Tooltip>
          </Upload>
          
          {/* 统一的多行输入框 */}
          <div className="flex-1 relative">
            <TextArea
              ref={textAreaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={placeholderText}
              disabled={isLoading}
              autoSize={{ minRows: 1, maxRows: 6 }}
              className="resize-none"
              style={{ borderRadius: 14, padding: '10px 14px', boxShadow: 'inset 0 1px 2px rgba(15,23,42,0.03)' }}
            />
          </div>
          
          {/* 发送按钮 */}
          <Button
            type="primary"
            onClick={onSend}
            disabled={isLoading || (!input.trim() && !selectedFile)}
            icon={<SendOutlined />}
            size="large"
            loading={isLoading}
            style={{ borderRadius: 12, minWidth: 110, boxShadow: '0 12px 24px rgba(31,111,235,0.18)' }}
          >
            {isLoading ? '发送中' : '发送'}
          </Button>
        </div>
        
        {/* 提示信息 */}
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between" style={{ gap: 12 }}>
          <span>
            💡 支持上传Excel(.xlsx, .xls)或CSV文件进行数据分析
          </span>
          <span className="text-gray-400">
            Enter发送 • Shift+Enter换行
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
