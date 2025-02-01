from flask import Flask, request, jsonify
from flask_cors import CORS
from pinecone import Pinecone
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Fix CORS configuration
CORS(app, resources={r"/api/*": {"origins": "https://tatweer-chat-app-demo.netlify.app"}})  # Remove trailing slash

# Global chat history (simple list)
chat_history = []

# API Keys and Configuration from environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "tatweer-rag-tf"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Connect to the index
index = pc.Index(INDEX_NAME) if PINECONE_API_KEY else None

# Initialize reranker
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Helper functions (unchanged)
def rephrase_query(user_query: str) -> str:
    """Rephrase the user query for better retrieval."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Rephrase this query for economic document retrieval while preserving intent:"},
            {"role": "user", "content": user_query}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

def rerank_results(query: str, chunks: list, top_k: int = 6) -> list:
    """Rerank chunks using cross-encoder."""
    pairs = [(query, chunk['metadata']['chunk_content']) for chunk in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [item[0] for item in ranked[:top_k]]

def generate_embeddings(text):
    """Generate embeddings using OpenAI."""
    try:
        return client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        ).data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def generate_gemini_response(prompt):
    """Generate a response using the Gemini API."""
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.2}
            }
        )
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def generate_response(user_input):
    """Generate a response to the user's input."""
    try:
        refined_query = user_input
        embedding = generate_embeddings(refined_query)
        if not embedding:
            return {"error": "Embedding generation failed"}

        query_response = index.query(vector=embedding, top_k=20, include_metadata=True)
        reranked_chunks = rerank_results(refined_query, query_response.matches)

        history_str = "\n".join(
            f"User: {entry['user']}\nBot: {entry['bot']}"
            for entry in chat_history[-3:]
        )

        context_str = "\n".join(
            f"{chunk['metadata']['chunk_content']}"
            for chunk in reranked_chunks[:6]
        )

        prompt = f"""Previous conversation:
                        {history_str}

                        You are an expert economic analyst. Your task is to provide detailed, structured, and accurate responses to user queries based on the context provided. Follow these guidelines:

                        1. **Structure Your Response**:
                        - Start with a clear title summarizing the topic.
                        - Use bullet points or numbered lists for clarity.
                        - Break down the response into logical sections (e.g., Overview, Key Sectors, Trends, Economic Indicators).

                        2. **For Financial Queries**:
                        - Include specific figures (e.g., $X billion, X%).
                        - Use financial formatting (e.g., $M/$B, percentages).
                        - Highlight key trends, comparisons, and changes over time.
                        - Provide formulas or calculations if relevant.

                        3. **For Descriptive Queries**:
                        - Explain concepts clearly and concisely.
                        - Use examples or analogies if helpful.
                        - Describe relationships between concepts or document types.

                        4. **Data Presentation**:
                        - Always include specific numbers and percentages.
                        - Compare data across years or sectors where applicable.
                        - Highlight notable trends, increases, or decreases.

                        5. **Tone and Language**:
                        - Respond in Arabic.
                        - Use a professional and informative tone.
                        - Avoid vague language; be precise and data-driven.

                        Context:
                        {context_str}

                        Query: {refined_query}

                        Example Response Format:
                        عنوان: نظرة عامة على النفقات المالية لعام 2014

                        إجمالي النفقات: $X تريليون

                        القطاعات الرئيسية:
                        • الدفاع: $X مليار (X% من الإجمالي)
                        • الرعاية الصحية: $X مليار (X% من الإجمالي)
                        • التعليم: $X مليار (X% من الإجمالي)
                        • البنية التحتية: $X مليار (X% من الإجمالي)
                        • الضمان الاجتماعي: $X مليار (X% من الإجمالي)

                        الاتجاهات البارزة:
                        • زيادة بنسبة X% في الإنفاق على الرعاية الصحية مقارنة بعام 2013
                        • انخفاض بنسبة X% في الإنفاق التقديري
                        • القطاع الأسرع نموًا: [القطاع] (+X%)
                        • أكبر انخفاض: [القطاع] (-X%)

                        المؤشرات الاقتصادية الرئيسية:
                        • الناتج المحلي الإجمالي: $X تريليون
                        • العجز: $X مليار
                        • نسبة الدين إلى الناتج المحلي الإجمالي: X%
                        • معدل التضخم: X%

                        [المصدر: file_name]"""

        gemini_response = generate_gemini_response(prompt)
        if not gemini_response:
            return {"error": "Response generation failed"}

        reranked_chunk_contents = [
            chunk['metadata']['chunk_content'] for chunk in reranked_chunks[:6]
        ]

        return {
            "analysis": gemini_response,
            "matches": reranked_chunks[:6],
            "reranked_chunk_contents": reranked_chunk_contents
        }
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

# Handle preflight requests
@app.route('/api/chat', methods=['OPTIONS'])
def handle_options():
    headers = {
        "Access-Control-Allow-Origin": "https://tatweer-chat-app-demo.netlify.app",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    return "", 204, headers

# Main chat endpoint
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        # Add CORS headers
        headers = {
            "Access-Control-Allow-Origin": "https://tatweer-chat-app-demo.netlify.app",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }

        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Invalid input"}), 400, headers

        user_message = data['message'].strip()
        result = generate_response(user_message)
        if "error" in result:
            return jsonify(result), 500, headers

        # Store in history after successful response
        chat_history.append({
            'user': user_message,
            'bot': result["analysis"]
        })

        # Keep history manageable (last 5 exchanges)
        if len(chat_history) > 5:
            chat_history.pop(0)

        return jsonify({
            "response": result["analysis"],
            "sources": [
                {
                    "source_id": f"Source {i+1}",
                    "content": chunk['metadata'].get('chunk_content', ''),
                    "type": chunk['metadata'].get('doc_type', 'unclassified'),
                    "score": chunk['score'],
                    "file_name": chunk['metadata'].get('file_name', 'Unknown'),
                    "file_url": chunk['metadata'].get('file_url', '#')
                } for i, chunk in enumerate(result["matches"])
            ],
            "reranked_chunk_contents": result["reranked_chunk_contents"]
        }), 200, headers
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500, headers

# Health check endpoint
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "ok",
        "pinecone": index is not None,
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY)
    })

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)