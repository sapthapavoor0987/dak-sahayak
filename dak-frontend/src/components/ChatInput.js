'use client';

import { useState, useRef, useEffect } from 'react';

const PLACEHOLDERS = {
  'English': 'Ask Dak Sahayak or enter PIN / Consignment No...',
  'Hindi': 'डाक सहायक से पूछें या पिन कोड / कंसाइनमेंट नंबर दर्ज करें...',
  'Kannada': 'ಡಾಕ್ ಸಹಾಯಕ್ ಅವರನ್ನು ಕೇಳಿ ಅಥವಾ ಪಿನ್ ಕೋಡ್ ನಮೂದಿಸಿ...',
  'Tamil': 'தபால் உதவியாளரிடம் கேளுங்கள் அல்லது பின் குறியீட்டை உள்ளிடவும்...',
  'Telugu': 'డాక్ సహాయక్‌ని అడగండి లేదా పిన్ కోడ్ నమోదు చేయండి...',
  'Marathi': 'डाक सहाय्यकला विचारा किंवा पिन कोड प्रविष्ट करा...',
  'Bengali': 'ডাক সহায়ককে জিজ্ঞাসা করুন বা পিন কোড লিখুন...'
};

export default function ChatInput({ onSend, disabled, language = 'English' }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const placeholder = PLACEHOLDERS[language] || PLACEHOLDERS['English'];

  return (
    <div className="input-section">
      <form onSubmit={handleSubmit} className="input-container">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />
        <button
          type="submit"
          className="send-action-btn"
          disabled={!text.trim() || disabled}
          title="Send message"
        >
          {disabled ? (
            <i className="fa-solid fa-spinner fa-spin"></i>
          ) : (
            <i className="fa-solid fa-arrow-up"></i>
          )}
        </button>
      </form>
      <p className="input-disclaimer">
        Dak Sahayak uses Google Gemini + Supabase Vector RAG. Answers are grounded in official India Post rules.
      </p>
    </div>
  );
}
