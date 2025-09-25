import os
import warnings
import traceback # Import the traceback module for detailed error logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from groq import Groq
from langchain_community.document_loaders import CSVLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

warnings.filterwarnings("ignore")

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

retriever = None

# --- Load API Key ---
try:
    GROQ_API_KEY = "your_key"
    client = Groq(api_key=GROQ_API_KEY)
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set.")
except Exception as e:
    print(f"API Key Error: {e}")

# --- Helper Function to Setup RAG Pipeline ---
def setup_rag_pipeline(file_path):
    """
    Loads a document, splits it, creates embeddings, and sets up a retriever.
    NOTE: This function will now raise an exception on failure instead of returning None.
    """
    try:
        print(f"Processing file: {file_path}")
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".csv"):
            loader = CSVLoader(file_path=file_path, csv_args={"delimiter": ","}, encoding="latin1")
        else:
            # Raise a specific error for unsupported file types
            raise ValueError("Unsupported file type. Please upload a CSV or PDF.")

        documents = loader.load()
        print(f"Loaded {len(documents)} document pages/rows.")
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        print(f"Split into {len(docs)} chunks.")

        print("Loading embedding model (this may take a moment on first run)...")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        print("Embedding model loaded.")

        print("Creating vector store...")
        db = Chroma.from_documents(docs, embeddings)
        print("Vector store created successfully.")
        
        return db.as_retriever()
    except Exception as e:
        # --- DETAILED ERROR LOGGING ---
        # Log the full error to the terminal for debugging
        print("\n--- DETAILED ERROR IN RAG PIPELINE ---")
        traceback.print_exc()
        print("----------------------------------------\n")
        # Re-raise the exception to be caught by the route handler
        raise e

# --- Define Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global retriever
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            retriever = setup_rag_pipeline(file_path)
            return jsonify({"success": f"File '{filename}' uploaded and processed successfully."})
        except Exception as e:
            # --- IMPROVED ERROR HANDLING ---
            # Catch the exception from setup_rag_pipeline and send its message to the frontend.
            # This provides a much more specific error to the user.
            return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route('/chat', methods=['POST'])
def chat():
    global retriever
    if not retriever:
        return jsonify({"error": "Document not uploaded or processed yet. Please upload a file first."}), 400

    user_query = request.json.get('message')
    if not user_query:
        return jsonify({"error": "No message provided"}), 400

    try:
        docs = retriever.get_relevant_documents(user_query)
        context = "\n".join([d.page_content for d in docs])

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Answer based ONLY on the context:\n{context}"},
                {"role": "user", "content": user_query}
            ],
            temperature=0
        )
        bot_response = completion.choices[0].message.content
        return jsonify({'response': bot_response})

    except Exception as e:
        print("\n--- DETAILED ERROR IN CHAT ---")
        traceback.print_exc()
        print("--------------------------------\n")
        return jsonify({"error": "Failed to get a response. Check server logs."}), 500

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

