// App.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import "./App.css";

// Arabic translations
const translations = {
  welcome: "مرحباً! كيف يمكنني مساعدتك اليوم؟",
  placeholder: "اكتب رسالتك...",
  header: "ماذا تريد أن تعرف اليوم؟",
  warning: "الذكاء الاصطناعي قد يخطئ. يرجى التحقق من المعلومات",
  error: "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.",
  networkError: "حدث خطأ في الاتصال"
};

const App = () => {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: translations.welcome,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Format time in Arabic
  const formatTime = (date) => {
    return new Date().toLocaleTimeString('ar-EG', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newMessage = {
      role: "user",
      content: input,
      timestamp: new Date()
    };

    const newMessages = [...messages, newMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: input,
        }),
      });

      if (!response.ok) {
        throw new Error(translations.networkError);
      }

      const data = await response.json();
      const assistantMessage = {
        role: "assistant",
        content: data.response,
        timestamp: new Date()
      };

      setMessages([...newMessages, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage = {
        role: "assistant",
        content: translations.error,
        timestamp: new Date()
      };
      setMessages([...newMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const MessageContent = ({ content, role }) => {
    if (role === "user") {
      return <div className="message-text">{content}</div>;
    }

    return (
      <div className="markdown-content">
        <ReactMarkdown
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || '');
              return !inline ? (
                <pre className="code-block" dir="ltr">
                  <code className={match ? `language-${match[1]}` : ''} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code className="inline-code" dir="ltr" {...props}>
                  {children}
                </code>
              );
            },
            a: ({ node, className, children, ...props }) => (
              <a className="markdown-link" {...props}>
                {children}
              </a>
            ),
            ul: ({ node, className, children, ...props }) => (
              <ul className="markdown-list" {...props}>
                {children}
              </ul>
            ),
            li: ({ node, className, children, ...props }) => (
              <li className="markdown-list-item" {...props}>
                {children}
              </li>
            ),
            p: ({ node, className, children, ...props }) => (
              <p dir="auto" {...props}>
                {children}
              </p>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className="chat-container" dir="rtl">
      <div className="chat-header">
        <h1>{translations.header}</h1>
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${
              message.role === "user" ? "user-message" : "assistant-message"
            }`}
          >
            <div className="message-content">
              <MessageContent content={message.content} role={message.role} />
              <span className="message-time" dir="ltr">
                {message.timestamp ? formatTime(message.timestamp) : formatTime(new Date())}
              </span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant-message">
            <div className="message-content loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={translations.placeholder}
            disabled={isLoading}
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()} 
            className="send-button"
            aria-label="إرسال"
          >
            <Send size={20} />
          </button>
        </div>
        <span className="warning-text">
          {translations.warning}
        </span>
      </form>
    </div>
  );
};

export default App;