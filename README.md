## **Web App Documentation**

### **Overview**

The web app is a **Retrieval-Augmented Generation (RAG)** system designed to provide detailed, structured, and accurate responses to user queries about economic and financial data. It integrates multiple APIs and services, including **OpenAI**, **Gemini**, and **Pinecone**, to retrieve and generate responses based on a large corpus of documents.

---

### **Backend Documentation**

#### **Technologies Used**

- **Flask**: A lightweight Python web framework for handling HTTP requests and responses.
- **Pinecone**: A vector database for semantic search and retrieval of relevant document chunks.
- **OpenAI**: Used for generating embeddings and rephrasing user queries.
- **Gemini**: A generative AI model for producing detailed and structured responses.
- **Sentence Transformers**: Used for reranking search results to improve relevance.

---

#### **Key Components**

1. **API Endpoints**

   - **`POST /api/chat`**: Handles user queries and returns a structured response.
     - **Input**: JSON payload with a `message` field containing the user's query.
     - **Output**: JSON response with:
       - `response`: The generated answer.
       - `sources`: Metadata for the retrieved documents.
       - `reranked_chunk_contents`: The content of the top reranked chunks.
   - **`GET /api/health`**: A health check endpoint to verify the status of the app and its dependencies.

2. **Core Functions**

   - **`rephrase_query`**: Rephrases the user query using GPT-4 to improve retrieval accuracy.
   - **`rerank_results`**: Reranks Pinecone search results using a cross-encoder model for better relevance.
   - **`generate_embeddings`**: Generates embeddings for the user query using OpenAI's `text-embedding-3-large` model.
   - **`generate_gemini_response`**: Generates a detailed and structured response using the Gemini API.
   - **`generate_response`**: Orchestrates the entire RAG pipeline, including query rephrasing, embedding generation, Pinecone search, reranking, and response generation.

3. **Data Flow**

   - The user query is sent to the `/api/chat` endpoint.
   - The query is rephrased using GPT-4.
   - Embeddings are generated for the rephrased query.
   - The embeddings are used to query the Pinecone index.
   - The search results are reranked using a cross-encoder model.
   - The top reranked chunks are passed to Gemini to generate a response.
   - The response, along with metadata and reranked chunk contents, is returned to the frontend.

4. **Environment Variables**
   - `PINECONE_API_KEY`: API key for Pinecone.
   - `OPENAI_API_KEY`: API key for OpenAI.
   - `GEMINI_API_KEY`: API key for Gemini.
   - `INDEX_NAME`: Name of the Pinecone index.

---

#### **Example Backend Workflow**

1. **User Query**:

   - The user sends a query: "Tell me about fiscal expenditures for 2014."

2. **Query Rephrasing**:

   - The query is rephrased to: "Provide an overview of fiscal expenditures for the year 2014."

3. **Embedding Generation**:

   - The rephrased query is converted into an embedding using OpenAI.

4. **Pinecone Search**:

   - The embedding is used to query the Pinecone index, retrieving the top 20 relevant chunks.

5. **Reranking**:

   - The retrieved chunks are reranked using a cross-encoder model to improve relevance.

6. **Response Generation**:

   - The top 6 reranked chunks are passed to Gemini to generate a structured response.

7. **Response Formatting**:
   - The response is formatted into sections (e.g., Overview, Key Sectors, Trends, Economic Indicators) and returned to the frontend.

---

### **Frontend Documentation**

#### **Technologies Used**

- **React**: A JavaScript library for building the user interface.
- **ReactMarkdown**: A component for rendering markdown content.
- **Lucide React**: Icons for the UI (e.g., send button).
- **CSS**: Custom styles for the chat interface.

---

#### **Key Components**

1. **State Management**

   - `messages`: Stores the chat history, including user queries and bot responses.
   - `input`: Stores the current user input.
   - `isLoading`: Tracks whether a request is in progress.

2. **Core Functions**

   - **`handleSubmit`**: Handles form submission, sends the user query to the backend, and updates the chat history.
   - **`clearHistory`**: Clears the chat history and removes it from `localStorage`.
   - **`MessageContent`**: A component that renders the content of each message, including markdown formatting and source links.

3. **Data Flow**

   - The user types a query and submits it.
   - The query is sent to the `/api/chat` endpoint.
   - The response is displayed in the chat interface, including the generated answer and source links.
   - The chat history is persisted in `localStorage` and restored on page reload.

4. **UI Components**
   - **Chat Header**: Displays the app title and a button to clear the chat history.
   - **Messages Container**: Displays the chat history, including user queries and bot responses.
   - **Input Form**: A form for the user to type and submit queries.

---

#### **Example Frontend Workflow**

1. **User Interaction**:

   - The user types a query and clicks the send button.

2. **Request Handling**:

   - The query is sent to the backend via the `/api/chat` endpoint.

3. **Response Display**:

   - The response is displayed in the chat interface, formatted with markdown and source links.

4. **Persistent History**:
   - The chat history is saved to `localStorage` and restored when the page is reloaded.

---

### **System Architecture**

```
Frontend (React) → Backend (Flask) → Pinecone → OpenAI → Gemini
```

1. **Frontend**:

   - Handles user interaction and displays responses.
   - Communicates with the backend via HTTP requests.

2. **Backend**:

   - Processes user queries, retrieves relevant data, and generates responses.
   - Integrates with Pinecone, OpenAI, and Gemini.

3. **Pinecone**:

   - Stores and retrieves document chunks based on semantic similarity.

4. **OpenAI**:

   - Generates embeddings for user queries and rephrases queries for better retrieval.

5. **Gemini**:
   - Generates detailed and structured responses based on retrieved data.

---

### **Environment Setup**

#### **Backend**

1. Install dependencies:
   ```bash
   pip install flask flask-cors pinecone-client openai requests python-dotenv sentence-transformers
   ```
2. Set environment variables:
   ```bash
   export PINECONE_API_KEY="your_pinecone_api_key"
   export OPENAI_API_KEY="your_openai_api_key"
   export GEMINI_API_KEY="your_gemini_api_key"
   ```
3. Run the Flask app:
   ```bash
   python app.py
   ```

#### **Frontend**

1. Install dependencies:
   ```bash
   npm install react-markdown lucide-react
   ```
2. Run the React app:
   ```bash
   npm start
   ```

---

### **Future Enhancements**

1. **Track history better**: Backend history accurately reflects what's shown in the front-end.
2. **Prompt refinement**: Refine prompt.
3. **Multi-Language Support**: Support additional languages.
