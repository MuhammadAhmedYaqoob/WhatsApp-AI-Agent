import json
import os
from loguru import logger
from openai import OpenAI
import openai
import requests
import PyPDF2 
from dotenv import load_dotenv
# from io import BytesIO
# import docx
# from datetime import datetime

# from io import BytesIO
# import requests
# import docx
# from langchain.docstore.document import Document  # Import the Document class

load_dotenv()

# Configuration parameters
INSTANCE_ID = os.getenv('INSTANCE_ID')
API_TOKEN = os.getenv('API_TOKEN')

from openai import OpenAI


# Load OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)


def check_zeus_inquery(chat_id, message):

    system_prompt = "Determine if the {message} is an inquiry matching or have same meanings with given phrases. phrases: 'I want to know about your iptv service', 'Tell me about your services', 'Tell me details regarding your iptv service', 'Details regarding your iptv'. Reply only with 'YES' if it is, otherwise reply with 'NO' and nothing else."
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content":message}
        ],
        max_tokens=5,
        temperature=0
    )

    if response.choices[0].message.content.strip().upper() == "YES":
        #pre defined message.
        send_message(chat_id, "Here are some essential details regarding our IPTV service that you should be aware of before we start. Kindly read the attached PDF Document. If you have any queries, please let me know.\n\n_Replied by *ZEUS AI BOT* ✨")
        #pdf file.
        url = f"https://waapi.app/api/v1/instances/{INSTANCE_ID}/client/action/send-media"
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "chatId": chat_id,
            "mediaUrl": "http://www.smilingskies.com/Details.pdf",
            "asDocument":True
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.success(f"Sent message to {chat_id}: {response.status_code} - {response.text}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False    

    else:
        return False    




def check_troubleshoot_inquery(chat_id, message):

    system_prompt = "Determine if the {message} is an inquiry related to troubleshooting or problems in installations, buffering, playbacks etc. For example: These days I am experiencing frequent buffering issues or sometimes the streaming is too slow. What should I do? Reply only with 'YES' if it is, otherwise reply with 'NO' and nothing else."
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content":message}
        ],
        max_tokens=5,
        temperature=0
    )

    if response.choices[0].message.content.strip().upper() == "YES":
        #pre defined message.
        send_message(chat_id, "Here are some essential details regarding Troubleshooting problems. Kindly read the attached PDF Document. If you have any queries, please let me know.\n\n_Replied by *ZEUS AI BOT* ✨")
        #pdf file.
        url = f"https://waapi.app/api/v1/instances/{INSTANCE_ID}/client/action/send-media"
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "chatId": chat_id,
            "mediaUrl": "http://www.smilingskies.com/troubleshoot.pdf",
            "asDocument":True
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.success(f"Sent message to {chat_id}: {response.status_code} - {response.text}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False    

    else:
        return False    


def send_message(chat_id, message):
    """Sends a message via the WhatsApp API."""

    url = f"https://waapi.app/api/v1/instances/{INSTANCE_ID}/client/action/send-message"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "chatId": chat_id,
        "message": message,
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        logger.success(f"Sent message to {chat_id}: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")


def extract_pdf_text(file_path):
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        return text

def get_output(message_body):
    # 2. Extract content from rag.pdf
    pdf_text = extract_pdf_text("rag.pdf")

    # Build messages for each user query
    messages = [
        {"role": "system", "content": "You are Zeus AI, a helpful IPTV customer support assistant. Answer user questions only based on the following document content. Make sure that you provide the exact answer found in the context, no changings from your side. If any emoji, send them too in answer. Response Formatting:Use bold text and bullet points where required (there should never be 2 stearicks * around any word or words). Append (line break and then 1 line gap here) 'Replied by ZEUS AI BOT ✨' at the end of every response. In troubleshooting questions, answer must be in the if and than form like under the solution steps are mentioned, don't show them sequentially, reply them as if and then. Don't change it. And make sure that answer should be summarize with maintaing all the important tokens"},
        {"role": "system", "content": f"Document:\n{pdf_text}"},
        {"role": "user", "content": message_body} 
    ]

    response = client.chat.completions.create(
        model="gpt-4.1-mini", 
        messages=messages,
        temperature=0.3
    )

    ai_response = response.choices[0].message.content
    return ai_response


