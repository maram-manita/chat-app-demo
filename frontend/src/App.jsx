import React, { useState, useRef, useEffect } from "react";
import { Delete, Send, Trash } from "lucide-react"; // Import Trash icon
import ReactMarkdown from "react-markdown";
import "./App.css";
import { MuiMarkdown, getOverrides } from "mui-markdown";

// Arabic translations
const translations = {
  welcome: "مرحباً! كيف يمكنني مساعدتك اليوم؟",
  placeholder: "اكتب رسالتك...",
  header: "ماذا تريد أن تعرف اليوم؟",
  warning: "الذكاء الاصطناعي قد يخطئ. يرجى التحقق من المعلومات",
  error: "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.",
  networkError: "حدث خطأ في الاتصال",
};

// Load initial state from localStorage
const getInitialState = () => {
  const savedHistory = localStorage.getItem("chatHistory");
  return savedHistory
    ? JSON.parse(savedHistory)
    : [
        {
          role: "assistant",
          content: translations.welcome,
          timestamp: new Date().toISOString(),
        },
      ];
};

const App = () => {
  const [messages, setMessages] = useState(getInitialState);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Save to localStorage whenever messages change
  useEffect(() => {
    localStorage.setItem("chatHistory", JSON.stringify(messages));
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Format time in Arabic
  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString("ar-EG", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  // Clear chat history
  const clearHistory = () => {
    setMessages([
      {
        role: "assistant",
        content: translations.welcome,
        timestamp: new Date().toISOString(),
      },
    ]);
    localStorage.removeItem("chatHistory");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newMessage = {
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, newMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(
        "https://chat-app-demo-o25l.onrender.com/api/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: input,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(translations.networkError);
      }

      const data = await response.json();
      console.log(data.reranked_chunk_contents);
      const assistantMessage = {
        role: "assistant",
        content: data.response,
        sources: data.sources, // Include sources in the message
        timestamp: new Date().toISOString(),
      };

      setMessages([...newMessages, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage = {
        role: "assistant",
        content: translations.error,
        timestamp: new Date().toISOString(),
      };
      setMessages([...newMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const MessageContent = ({ content, role, sources }) => {
    if (role === "user") {
      return <div className="message-text">{content}</div>;
    }

    return (
      <div className="markdown-content">
        <MuiMarkdown
          overrides={{
            ...getOverrides({}), // Keeps other default overrides
            h1: {
              component: "p",
              props: {
                style: {
                  fontSize: "32px",
                  fontWeight: "bold",
                  wordSpacing: "-0.1em",
                  margin: "8px 0",
                },
              },
            },
            h2: {
              component: "p",
              props: {
                style: {
                  fontSize: "24px",
                  fontWeight: "bold",
                  wordSpacing: "-0.1em",
                  margin: "4px 0",
                },
              },
            },
            h3: {
              component: "p",
              props: {
                style: {
                  fontSize: "16px",
                  fontWeight: "bold",
                  wordSpacing: "-0.1em",
                  margin: "4px 0",
                },
              },
            },
            h4: {
              component: "p",
              props: {
                style: {
                  fontSize: "16px",
                  fontWeight: "bold",
                  wordSpacing: "-0.1em",
                  margin: "4px 0",
                  fontColor: "red",
                },
              },
            },
            p: {
              component: "p",
              props: {
                style: {
                  // marginTop: "4px",
                },
              },
            },
            ul: {
              component: "p",
              props: {
                style: {
                  marginRight: "12px",
                },
              },
            },
          }}
        >
          {content}
        </MuiMarkdown>

        {/* Render sources as clickable links */}
        {sources && sources.length > 0 && (
          <div className="sources-container">
            <h4>المصادر:</h4>
            <ul>
              {sources.map((source, index) => (
                <li key={index}>
                  <a
                    href={source.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-link"
                  >
                    {source.file_name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="chat-container" dir="rtl">
      <div className="messages-container">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${
              message.role === "user" ? "user-message" : "assistant-message"
            }`}
          >
            <div className="message-content">
              <MessageContent
                content={message.content}
                role={message.role}
                sources={message.sources}
              />
              <span className="message-time" dir="ltr">
                {message.timestamp
                  ? formatTime(message.timestamp)
                  : formatTime(new Date())}
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
        <div className="bottom-section">
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
              <Send size={24} />
            </button>
          </div>
          <button onClick={clearHistory} className="clear-button">
            <Trash />
          </button>
        </div>
        <span className="warning-text" style={{ marginRight: "20px" }}>
          {translations.warning}
        </span>
      </form>
    </div>
  );
};

export default App;
