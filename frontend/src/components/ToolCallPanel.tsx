import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import type { StreamEvent, ToolCallStateItem } from '../types';

interface ToolCallPanelProps {
  events: StreamEvent[];
  toolCalls: ToolCallStateItem[];
  isStreaming: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
}

// Helper render json as code block markdown
const codeBlock = (obj: any) => '```json\n' + JSON.stringify(obj, null, 2) + '\n```';

const ToolCallPanel: React.FC<ToolCallPanelProps> = ({ events, toolCalls, isStreaming, collapsed, onToggle }) => {
  const [internalCollapsed, setInternalCollapsed] = useState(collapsed ?? true);
  useEffect(() => { if (collapsed !== undefined) setInternalCollapsed(collapsed); }, [collapsed]);
  const toggle = () => { if (onToggle) onToggle(); else setInternalCollapsed(c => !c); };

  const finalEvent = events.find(e => e.event === 'final_answer');
  const headerStatus = isStreaming
    ? '工具调用中…'
    : finalEvent ? '工具调用完成 ✅' : '工具调用记录';

  return (
    <div className="w-full border border-gray-300 rounded-lg bg-white shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 cursor-pointer" onClick={toggle}>
        <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <span>🛠️ 工具调用链</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${isStreaming ? 'bg-blue-500 text-white animate-pulse' : 'bg-green-500 text-white'}`}>{headerStatus}</span>
        </div>
          {internalCollapsed ? '展开 ▾' : '收起 ▴'}
      </div>
      {!internalCollapsed && (
        <div className="max-h-96 overflow-y-auto p-4 space-y-4 text-xs leading-relaxed">
          {toolCalls.length === 0 && (
            <p className="text-gray-500">暂无工具调用计划。</p>
          )}
          {toolCalls.map(call => (
            <div key={call.id} className="border border-gray-200 rounded-md p-3 bg-gray-50">
              <div className="flex items-center justify-between mb-1">
                <div className="font-semibold text-gray-800">{call.name}</div>
                <div className="text-xs">
                  {call.status === 'pending' && <span className="text-gray-500">等待</span>}
                  {call.status === 'running' && <span className="text-blue-600">执行中…</span>}
                  {call.status === 'success' && <span className="text-green-600">成功</span>}
                  {call.status === 'error' && <span className="text-red-600">失败</span>}
                </div>
              </div>
              <details className="mb-2" open>
                <summary className="cursor-pointer text-gray-700">参数</summary>
                <div className="mt-1">
                  <ReactMarkdown>{codeBlock(call.arguments)}</ReactMarkdown>
                </div>
              </details>
              {call.result && (
                <details className="mb-2" open>
                  <summary className="cursor-pointer text-gray-700">结果</summary>
                  <div className="mt-1">
                    <ReactMarkdown>{codeBlock(call.result)}</ReactMarkdown>
                  </div>
                </details>
              )}
              {call.error && (
                <div className="text-red-600">错误: {call.error}</div>
              )}
              <div className="text-gray-400 text-[10px] mt-1">
                {call.startedAt && <span>开始: {new Date(call.startedAt).toLocaleTimeString()} </span>}
                {call.finishedAt && <span>结束: {new Date(call.finishedAt).toLocaleTimeString()}</span>}
              </div>
            </div>
          ))}
          {finalEvent && (
            <div className="border border-green-300 bg-green-50 text-green-700 rounded-md p-3">
              <div className="font-semibold mb-1">最终回答</div>
              <ReactMarkdown>{(finalEvent.data as any).content || ''}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolCallPanel;
