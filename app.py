from flask import Flask, request, jsonify, session 
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
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Set your secret key

# Fix CORS configuration
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Remove trailing slash

# API Keys and Configuration from environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "tatweer-rag-no-context"
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

# ------------------- Modified Rephrase Function -------------------
def rephrase_query(user_query: str, context: str) -> str:
    """
    Rephrase the user query for economic document retrieval while preserving intent,
    and taking into account the provided context.
    """
    prompt = f"""Based on the following conversation context:
{context}

importent: try always to write year, ex:"if recently is written write 2024"

Rephrase this query for economic document retrieval while preserving its original intent:"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

# ------------------- Other Helper Functions -------------------
def rerank_results(query: str, chunks: list, top_k: int = 8) -> list:
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

def generate_response(user_input, chat_history):
    """Generate a response to the user's input using session-specific chat history."""
    try:
        # Prepare context from recent conversation history (if available)
        history_str = "\n".join(
            f"User: {entry['user']}\nBot: {entry['bot']}"
            for entry in chat_history[-3:]
        ) if chat_history else "لا توجد محادثة سابقة."

        # Use the context when rephrasing the query
        #refined_query = rephrase_query(user_input, history_str)
        
        # Generate embeddings from the refined query
        embedding = generate_embeddings(user_input)
        if not embedding:
            return {"error": "Embedding generation failed"}

        query_response = index.query(vector=embedding, top_k=30, include_metadata=True)
        reranked_chunks = rerank_results(user_input, query_response.matches)

        # Build context using the top 7 chunks
        context_str = "\n".join(
            f"{chunk['metadata']['chunk_content']}"
            for chunk in reranked_chunks[:8]
        )

        # Also capture the unused chunks (if any) beyond the top 7 for later question suggestion
        unused_chunks = [chunk['metadata']['chunk_content'] for chunk in reranked_chunks[7:]]

        prompt = f"""Previous conversation:
{history_str}

You are an expert economic analyst. Your task is to provide detailed, structured, and accurate responses to user queries based on the context provided. Follow these guidelines:

NOTE: use the most recent information from the information are provided to you.

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

Query: {user_input}

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
"""
        gemini_response = generate_gemini_response(prompt)
        if not gemini_response:
            return {"error": "Response generation failed"}

        reranked_chunk_contents = [
            chunk['metadata']['chunk_content'] for chunk in reranked_chunks[:6]
        ]

        return {
            "analysis": gemini_response,
            "matches": reranked_chunks[:7],
            "reranked_chunk_contents": reranked_chunk_contents,
            "unused_chunks": unused_chunks  # include unused info for follow-up suggestions
        }
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

# ------------------- Endpoints -------------------
@app.route('/api/chat', methods=['OPTIONS'])
def handle_options():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    return "", 204, headers

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }

        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Invalid input"}), 400, headers

        user_message = data['message'].strip()

        # Retrieve or initialize session chat history
        chat_history = session.get('chat_history', [])

        result = generate_response(user_message, chat_history)
        if "error" in result:
            return jsonify(result), 500, headers

        # Append the new exchange to the user's session history
        chat_history.append({
            'user': user_message,
            'bot': result["analysis"]
        })

        # Limit history to the last 5 exchanges
        if len(chat_history) > 5:
            chat_history = chat_history[-5:]
        session['chat_history'] = chat_history

        # Save the unused chunk information in the session for question suggestions
        session['unused_chunks'] = result.get("unused_chunks", [])

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

@app.route('/api/suggestions', methods=['OPTIONS'])
def suggestions_options():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    return "", 204, headers

@app.route('/api/suggestions', methods=['POST'])
def suggestions_endpoint():
    """
    This endpoint generates suggestions for the next three follow-up questions.
    It uses the unused information from the retrieved chunks (stored in the session)
    to generate suggestions.
    """
    try:
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        data = request.get_json() or {}

        # Check if there is unused info stored in the session
        unused_info = session.get('unused_chunks')
        if unused_info:
            unused_info_str = "\n".join(unused_info)
        else:
            unused_info_str = "لا توجد معلومات غير مستخدمة من المستندات المسترجعة."

        # Optionally, also include recent conversation if available
        chat_history = session.get('chat_history', [])
        if chat_history:
            conversation = "\n".join(
                f"User: {entry['user']}\nBot: {entry['bot']}"
                for entry in chat_history[-3:]
            )
        else:
            conversation = "لا توجد محادثة سابقة."

        prompt = f"""السياق من المحادثة السابقة:
{conversation}

المعلومات غير المستخدمة من المستندات المسترجعة:
{unused_info_str}

بصفتك محلل اقتصادي خبير، اقترح ثلاث أسئلة متابعة يمكن أن يطرحها المستخدم لاستكشاف الموضوع بشكل أعمق بناءً على المعلومات أعلاه.
يُرجى تقديم الاقتراحات في شكل نقاط مختصرة.
الإجابة يجب أن تكون باللغة العربية.
لا تكتب اسئله غير واضحه اذكر ماهو الموضوع
اعطني الثلاث اسئله فقط دون أي كلمات إضافية.
لا تستعمل تنسيق markdown.
"""
        suggestions = generate_gemini_response(prompt)
        if suggestions is None:
            return jsonify({"error": "فشل توليد الاقتراحات"}), 500, headers

        # Split the response into a list of suggestions (ignoring empty lines)
        suggestions_list = [line.strip() for line in suggestions.split("\n") if line.strip()]

        return jsonify({"suggestions": suggestions_list}), 200, headers
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500, headers

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "ok",
        "pinecone": index is not None,
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
