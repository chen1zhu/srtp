import React, { useState } from 'react';
import { Modal, Button } from 'antd';
import { ZoomInOutlined, DownloadOutlined } from '@ant-design/icons';

interface ImagePreviewProps {
  src: string;
  alt: string;
  fileName: string;
  className?: string;
}

const ImagePreview: React.FC<ImagePreviewProps> = ({ 
  src, 
  alt, 
  fileName, 
  className = '' 
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(src);
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
      console.error('下载图片失败:', error);
    }
  };

  return (
    <>
      <div className={`relative group cursor-pointer ${className}`}>
        <img 
          src={src} 
          alt={alt}
          className="max-w-full h-auto rounded border transition-transform hover:scale-105"
          style={{ maxHeight: '200px' }}
          onClick={() => setIsModalVisible(true)}
        />
        
        {/* 悬浮操作按钮 */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-200 rounded flex items-center justify-center opacity-0 group-hover:opacity-100">
          <div className="flex space-x-2">
            <Button 
              type="primary" 
              shape="circle" 
              icon={<ZoomInOutlined />}
              size="small"
              onClick={() => setIsModalVisible(true)}
              title="查看大图"
            />
            <Button 
              shape="circle" 
              icon={<DownloadOutlined />}
              size="small"
              onClick={handleDownload}
              title="下载图片"
            />
          </div>
        </div>
      </div>

      {/* 图片预览模态框 */}
      <Modal
        title={
          <div className="flex items-center justify-between">
            <span>{fileName}</span>
            <Button 
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              size="small"
            >
              下载
            </Button>
          </div>
        }
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width="90%"
        style={{ maxWidth: '1200px' }}
        centered
      >
        <div className="text-center">
          <img 
            src={src} 
            alt={alt}
            className="max-w-full h-auto"
            style={{ maxHeight: '70vh' }}
          />
        </div>
      </Modal>
    </>
  );
};

export default ImagePreview;
