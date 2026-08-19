'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageBubble({ role, content, isStreaming = false }) {
  const [copied, setCopied] = useState(false);
  const isBot = role === 'assistant' || role === 'bot';

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`message-row ${isBot ? 'bot' : 'user'}`}>
      {isBot && (
        <div className="message-avatar bot">
          <i className="fa-solid fa-robot"></i>
        </div>
      )}

      <div className="message-bubble">
        {isBot ? (
          <div className="bot-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
            {isStreaming && <span className="typing-cursor"></span>}
            {!isStreaming && content && (
              <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
                <button
                  onClick={handleCopy}
                  style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.04)' }}
                  title="Copy response"
                >
                  <i className={copied ? 'fa-solid fa-check text-green' : 'fa-regular fa-copy'}></i>
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <div>{content}</div>
        )}
      </div>

      {!isBot && (
        <div className="message-avatar user">
          <i className="fa-solid fa-user"></i>
        </div>
      )}
    </div>
  );
}
