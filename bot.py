import re
import fitz  # PyMuPDF for PDF extraction
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

# Load OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# PDF File Path
pdf_path = "rag.pdf"

# Step 1: Extract Q&A from PDF
def extract_qa_pairs(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"

    qa_pairs = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("Q:"):
            question = lines[i].strip()
            answer = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("Q:"):
                if lines[i].strip():
                    answer.append(lines[i].strip())
                i += 1
            qa_pairs.append((question, " ".join(answer)))
        else:
            i += 1
    return qa_pairs

qa_data = extract_qa_pairs(pdf_path)

# Step 2: Create FAISS Vector Store
dimension = 384  # Embedding dimension for MiniLM
index = faiss.IndexFlatL2(dimension)
qa_texts = []
qa_embeddings = []

for question, answer in qa_data:
    text = f"{question}\n{answer}"
    embedding = embed_model.encode(text).astype(np.float32)
    index.add(np.array([embedding]))
    qa_texts.append(text)
    qa_embeddings.append(embedding)

# Step 3: Define RAG Search
def retrieve_context(query, top_k=8):
    query_embedding = embed_model.encode(query).astype(np.float32)
    distances, indices = index.search(np.array([query_embedding]), top_k)
    retrieved_texts = [qa_texts[i] for i in indices[0] if i < len(qa_texts)]
    return retrieved_texts


# Step 4: Generate Answer using OpenAI GPT with conversation history support
def generate_answer(query, context, googlesheetdata_context, conversation_history=""):
    """Generate a response using OpenAI GPT with retrieved RAG context and conversation history."""
    context_text = "\n".join(context) if context else "No relevant context found."
    googlesheetdata_context_text = googlesheetdata_context if googlesheetdata_context else "No relevant data found regarding customer from google sheet database."
    
    # Include conversation history section if available
    history_section = ""
    if conversation_history and conversation_history.strip():
        history_section = f"""
        Previous Conversation History:
        {conversation_history}
        """

    prompt = f"""
    You are an AI assistant that provides responses in English.
    {history_section}
    Current Question: {query}
    
    Relevant Information: 
    {context_text}

    Customer Information:
    {googlesheetdata_context_text}

    - You are an intelligent AI AGENT named ZEUS, designed to assist users with their queries in the query mode as a customer service agent.
    
    - Guidelines:
      - If users ask for personal information, use the customer's details provided above and respond accordingly.
      - If the user asks a question related to troubleshooting (e.g., buffering, playback errors, offline issues, or device performance), provide relevant troubleshooting steps.
      - Always maintain context from the conversation history - reference previous questions and answers when appropriate.
      - If the user is following up on a previous question or troubleshooting step, acknowledge this and continue from where you left off.

    - Guard Rails:
      - Apologize to the user if their query is not related to services.

    - Response Formatting:
      - Use bold text and bullet points where required (there should never be 2 stearicks * around any word or words).
      - Append (line break and then 1 line gap here) 'Replied by ZEUS AI BOT ✨' at the end of every response.

    - Context Matching and Response Rules:
      - If a query exactly matches or is semantically equivalent to an entry in the Zeus TV FAQ/database (covering topics like application installation, payment issues, subscription plans, etc.), respond solely based on that answer.
      - If the context suggests the prompt is leading to another question, ask that question first to gather more information before replying.
      - If no match is found in the FAQ, proceed as a general customer assistant.
    
    - Troublingshooting related questions:
      - In troubleshooting questions, the steps should be mention with the following form (after following step 1(details of step 1) if issue still persists follow step2 (details of step2) .. ) as mentioned in the answer. Don't change it.
      
    """
    
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant named ZEUS."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return completion.choices[0].message.content.strip()

def get_bot_response(query, googlesheetdata, conversation_history=""):
    """
    Generate a response based on the message, customer context, and conversation history
    
    Args:
        query: The current message from the customer
        googlesheetdata: Customer information from Google Sheets
        conversation_history: String containing the formatted conversation history
        
    Returns:
        AI-generated response with proper formatting
    """
    # Retrieve relevant context
    context = retrieve_context(query)
    
    # Generate AI response with conversation history
    answer = generate_answer(query, context, googlesheetdata, conversation_history)

    # Sanitize: Replace multiple asterisks with a single one
    cleaned_answer = re.sub(r'\*{2,}', '*', answer)

    return cleaned_answer