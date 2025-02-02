import React, { useState, useRef, useEffect, useCallback } from "react";
import { Send, Trash } from "lucide-react"; // Using icons for send and clear history
import { MuiMarkdown, getOverrides } from "mui-markdown";
import "./App.css";

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

// Component to render each message
const Message = ({ message, formatTime }) => {
  const { role, content, sources, timestamp } = message;
  return (
    <div className={`message ${role === "user" ? "user-message" : "assistant-message"}`}>
      <div className="message-content">
        {role === "user" ? (
          <div className="message-text">{content}</div>
        ) : (
          <div className="markdown-content">
            <MuiMarkdown
              overrides={{
                ...getOverrides({}),
                h1: {
                  component: "p",
                  props: {
                    style: {
                      fontSize: "32px",
                      fontWeight: "bold",
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
                      margin: "4px 0",
                      color: "red",
                    },
                  },
                },
                p: { component: "p", props: {} },
                ul: {
                  component: "ul",
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

            {/* Render sources as clickable links, if provided */}
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
        )}
        <span className="message-time" dir="ltr">
          {timestamp ? formatTime(timestamp) : formatTime(new Date())}
        </span>
      </div>
    </div>
  );
};

const App = () => {
  const [messages, setMessages] = useState(getInitialState);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("chatHistory", JSON.stringify(messages));
  }, [messages]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
    const welcomeMessage = {
      role: "assistant",
      content: translations.welcome,
      timestamp: new Date().toISOString(),
    };
    setMessages([welcomeMessage]);
    localStorage.removeItem("chatHistory");
  };

  // Send a message to the /api/chat endpoint and update the conversation.
  const sendMessage = async (messageText) => {
    const userMessage = {
      role: "user",
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: messageText }),
      });
      if (!response.ok) throw new Error(translations.networkError);
      const data = await response.json();
      const assistantMessage = {
        role: "assistant",
        content: data.response,
        sources: data.sources, // optional: list of sources
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage = {
        role: "assistant",
        content: translations.error,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle form submission (user sending a message)
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    await sendMessage(input);
    setInput("");
  };

  // Debounced fetch for suggestions
  const fetchSuggestions = useCallback(() => {
    const getSuggestions = async () => {
      try {
        let conversationText = "";
        if (messages.length > 0) {
          // Use the last three exchanges to build the conversation context.
          const recentMessages = messages.slice(-3);
          conversationText = recentMessages
            .map((msg) =>
              msg.role === "user"
                ? `User: ${msg.content}`
                : `Bot: ${msg.content}`
            )
            .join("\n");
        } else {
          conversationText = "لا توجد محادثة سابقة.";
        }
        const response = await fetch("http://localhost:5000/api/suggestions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation: conversationText }),
        });
        if (!response.ok) throw new Error("Error fetching suggestions");
        const data = await response.json();
        setSuggestions(data.suggestions);
      } catch (error) {
        console.error("Error fetching suggestions:", error);
        setSuggestions([]);
      }
    };

    // Debounce for 500ms
    const timeoutId = setTimeout(() => {
      getSuggestions();
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [messages]);

  // Fetch suggestions after every assistant response
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === "assistant") {
      const clearDebounce = fetchSuggestions();
      return clearDebounce;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, fetchSuggestions]);

  // When a suggestion button is clicked, send that suggestion as a new message
  // and clear the suggestions.
  const handleSuggestionClick = (suggestion) => {
    if (!isLoading) {
      sendMessage(suggestion);
      setSuggestions([]); // Clear the suggestions after selection
    }
  };

  return (
    <div className="chat-container" dir="rtl">
      {/* Header */}
      <header className="chat-header">
        <h1>{translations.header}</h1>
      </header>

      <div className="messages-container">
        {messages.map((message, index) => (
          <Message key={index} message={message} formatTime={formatTime} />
        ))}

        {/* Render suggestions vertically under the last message */}
        {suggestions && suggestions.length > 0 && (
          <div className="suggestions-container">
            {suggestions.slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-button"
                onClick={() => handleSuggestionClick(suggestion)}
                title="اقترح متابعة"
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

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

      {/* Input and Controls */}
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="bottom-section">
          <div className="input-container">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={translations.placeholder}
              disabled={isLoading}
              aria-label="رسالة المستخدم"
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
          <button
            type="button"
            onClick={clearHistory}
            className="clear-button"
            aria-label="مسح التاريخ"
            title="مسح التاريخ"
          >
            <Trash size={24} />
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
