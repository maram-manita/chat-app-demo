from flask import Flask, request, jsonify
from flask_cors import CORS
from pinecone import Pinecone
from openai import OpenAI
import os
import requests


app = Flask(__name__)
CORS(app)

# Global chat history (simple list)
chat_history = []

# API Keys and Configuration from environment variables
PINECONE_API_KEY = "pcsk_BKerG_Q89WDmxHRMcj37fTbfij2t6GtwjEp4akXWvQ2AYVJDFCA97aWFNTyZQoqd3c34u"
INDEX_NAME = "tatweer-rag-tf"
GEMINI_API_KEY = 'AIzaSyB59KEExXDIVvkUljOLCY4iBusHfjgwYmk'
OPENAI_API_KEY = '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'
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp" 

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Connect to the index
index = pc.Index(INDEX_NAME) if PINECONE_API_KEY else None

def generate_embeddings(text):
    try:
        return client.embeddings.create(
            model="text-embedding-3-large",  # Ensure this model is available in your OpenAI account
            input=text
        ).data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def generate_gemini_response(prompt):
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.2}
            }
        )
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def generate_response(user_input):
    try:
        # Format chat history for prompt
        history_str = "\n".join(
            f"User: {entry['user']}\nBot: {entry['bot']}" 
            for entry in chat_history[-3:]  # Keep last 3 exchanges
        )

        # Generate embeddings
        embedding = generate_embeddings(user_input)
        if not embedding:
            return {"error": "Embedding generation failed"}

        # Query Pinecone index
        query_response = index.query(vector=embedding, top_k=6, include_metadata=True)
        context_str = "\n".join(
            f"{match.metadata}"
            for match in query_response.matches[:6]
        )
        print('query_response  ',query_response)
        

        # Construct prompt with history and context
        prompt = f"""Previous conversation:
{history_str}

Respond according to:
- Financial queries: Show formulas, financial formatting ($M/$B), source conflicts
- Descriptive queries: Structural explanations, document types, concept relationships
Always reference sources file name at the end of the answer 
Respond in Arabic.
Context:
{context_str}

Query: {user_input}

Format: Provide the response in markdown format.
[المصدر]: file name at the end of the answer"""

        # Generate response using Gemini
        gemini_response = generate_gemini_response(prompt)
        if not gemini_response:
            return {"error": "Response generation failed"}
        

        return {
            "analysis": gemini_response,
            "matches": query_response.matches[:6]
        }
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Invalid input"}), 400

        user_message = data['message'].strip()
        result = generate_response(user_message)
        if "error" in result:
            return jsonify(result), 500

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
                    "content": match.metadata.get('text', ''),
                    "type": match.metadata.get('doc_type', 'unclassified'),
                    "score": match.score
                } for i, match in enumerate(result["matches"])
            ]
        })
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

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

