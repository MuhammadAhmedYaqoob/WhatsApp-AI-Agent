import json
import os
import threading
import time
from bot import get_bot_response
from dotenv import load_dotenv
import openai
import gspread
import requests
from loguru import logger
from google.oauth2 import service_account
from utils import send_message, check_zeus_inquery, check_troubleshoot_inquery
from flask import Flask, request, jsonify

load_dotenv()

# Configuration parameters from environment variables
INSTANCE_ID = os.getenv('INSTANCE_ID')
API_TOKEN = os.getenv('API_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Google Sheets setup
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = service_account.Credentials.from_service_account_file(
    'zeus-registration-form-0250d4aaef74.json', scopes=scope
)
client = gspread.authorize(creds)
sheet_id = os.getenv('sheet_id')
sheet = client.open_by_key(sheet_id)
worksheet1 = sheet.get_worksheet(0)  # Main worksheet

app = Flask(__name__)

# Global set to track processed message IDs
processed_message_ids = set()

# Constants for session management
MAX_HISTORY_PAIRS = 10  # Store last 10 conversation exchanges
SESSION_TIMEOUT = 120.0  

# Active sessions dictionary
active_sessions = {}
active_sessions_lock = threading.Lock()


# python runing.. 
# flask local hostel -> local host , port 80 activate, http listen 
# apis (endpoint)
# ngrok (static ip)

# waapi.app 

# phonebumber + ngork

# python main.py 
# ngork/ nginix .... port number (80)



@app.route(f"/instance/{INSTANCE_ID}", methods=['GET'])
def verify_webhook():
    hub_challenge = request.args.get('hub.challenge')
    hub_verify_token = request.args.get('hub.verify_token')
    
    if hub_verify_token == VERIFY_TOKEN:
        logger.success("Webhook verified successfully")
        return hub_challenge
    else:
        logger.error("Webhook verification failed")
        return "Verification token mismatch", 403

def cleanup_session(chat_id):
    """Cleanup session data after inactivity"""
    with active_sessions_lock:
        if chat_id in active_sessions:
            del active_sessions[chat_id]
            logger.info(f"Session cleaned up for {chat_id}")

def fetch_customer_context(normalized_chat_id):  # phone number 
    """Fetch customer details from Google Sheets"""
    try:
        testing_contacts_header = worksheet1.find("Testing Contacts")
        contacts_col_index = testing_contacts_header.col
        contacts = worksheet1.col_values(contacts_col_index)
        
        for i in range(2, len(contacts) + 1):
            if contacts[i - 1].strip() == normalized_chat_id:
                headers = worksheet1.row_values(1)
                row_values = worksheet1.row_values(i)
                return "\n".join(f"{h}: {v}" for h, v in zip(headers, row_values))
        
        logger.warning(f"Customer {normalized_chat_id} not found in Testing Contacts")
        return ""
    except Exception as e:
        logger.error(f"Error fetching customer details: {e}")
        return ""

def format_conversation_history(chat_id):
    """Format conversation history for the given chat_id in a way the LLM can understand"""
    try:
        with active_sessions_lock:
            if chat_id not in active_sessions:
                return ""
            
            
            with active_sessions[chat_id]['lock']:
                history = active_sessions[chat_id]['history']
                if not history:
                    return ""
                
                formatted_history = ""
                for i in range(0, len(history), 2):
                    if i+1 < len(history):
                        user_msg = history[i]['content']
                        bot_msg = history[i+1]['content']
                        formatted_history += f"Customer: {user_msg}\nZEUS: {bot_msg}\n\n"
                return formatted_history
    except Exception as e:
        logger.error(f"Error formatting history for {chat_id}: {e}")
        return ""  # Return empty string on error



def process_message(chat_id, message_body):
    """Core message processing logic"""
    normalized_chat_id = chat_id.lstrip('+').replace('@c.us', '')
    
    # Authorization check
    try:
        testing_contacts = worksheet1.col_values(worksheet1.find("Testing Contacts").col)
        testing_contacts = [num.strip() + "@c.us" for num in testing_contacts if num.strip()]
        ignore_contacts = worksheet1.col_values(worksheet1.find("Ignore Contacts").col)
    except Exception as e:
        logger.error(f"Error reading contacts: {e}")
        return "Service temporarily unavailable"

    if chat_id in ignore_contacts:
        logger.info(f"Ignoring message from {chat_id}")
        return ""
    
    if not any(norm_id == normalized_chat_id 
              for norm_id in [num.replace('+', '').replace('@c.us', '') 
                            for num in testing_contacts]):
        logger.warning(f"Unauthorized access attempt from {chat_id}")
        return ""

    # Session management
    with active_sessions_lock:
        session = active_sessions.setdefault(chat_id, {
            'lock': threading.Lock(),
            'timer': None,
            'history': [],
            'paused': False
        })
        
        if session['paused']:
            logger.info(f"Ignoring message from paused session {chat_id}")
            return ""
        
        # Reset inactivity timer
        if session['timer']:
            session['timer'].cancel()
        session['timer'] = threading.Timer(SESSION_TIMEOUT, cleanup_session, args=(chat_id,))
        session['timer'].start()


    # Check for admin takeover ("Hii" detection)
    def check_hii():
        WA_API_URL = f"https://waapi.app/api/v1/instances/{INSTANCE_ID}/client/action/fetch-messages"
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(WA_API_URL, 
                                   headers=headers,
                                   json={"chatId": chat_id, "limit": 1, "fromMe": True})
            if response.status_code == 200:
                messages = response.json().get("data", {}).get("data", [])
                if messages and messages[0].get("message", {}).get("body", "").strip() == "Hii":
                    with active_sessions_lock:
                        active_sessions[chat_id]['paused'] = True
                        if active_sessions[chat_id]['timer']:
                            active_sessions[chat_id]['timer'].cancel()
                        active_sessions[chat_id]['timer'] = threading.Timer(300.0, cleanup_session, args=(chat_id,))
                        active_sessions[chat_id]['timer'].start()
                    send_message(chat_id, "Admin has joined the chat.\n\n_Replied by *ZEUS AI BOT* ✨")
        except Exception as e:
            logger.error(f"Error checking messages: {e}")

    check_hii()
    
    # Get customer context and format conversation history
    customer_context = fetch_customer_context(normalized_chat_id)
    
    # Format the conversation history into a structure that the LLM can understand
    conversation_history = format_conversation_history(chat_id)
    
    # Get bot response with conversation history
    ai_response = get_bot_response(message_body, customer_context, conversation_history)
    
    # Update conversation history
    with active_sessions[chat_id]['lock']:
        active_sessions[chat_id]['history'].extend([
            {"role": "user", "content": message_body},
            {"role": "assistant", "content": ai_response}
        ])
        
        # Keep history within maximum size to prevent excessive memory usage and context overflow
        if len(active_sessions[chat_id]['history']) > MAX_HISTORY_PAIRS * 2:
            active_sessions[chat_id]['history'] = active_sessions[chat_id]['history'][-MAX_HISTORY_PAIRS*2:]

    if check_zeus_inquery(chat_id, message_body) == True:
        return ai_response.replace("**", "*")
    
    if check_troubleshoot_inquery(chat_id, message_body) == True:
        return ai_response.replace("**", "*")
    
    send_message(chat_id, ai_response)
    logger.success(f"Processed message from {chat_id}\nQuery: {message_body}\nResponse: {ai_response}")
    return ai_response.replace("**", "*")

def main(message_id, chat_id, message_body, has_media, testing=False):
    """Entry point for message processing"""
    if not (chat_id and message_id):
        return "Invalid data", 400

    if not testing and message_id in processed_message_ids:
        return "OK", 200
    
    processed_message_ids.add(message_id)
    logger.info(f"Processing message {message_id} from {chat_id}")
    
    # Media handling
    try:
        main_contacts = worksheet1.col_values(worksheet1.find("Testing Contacts").col)
        normalized_chat_id = chat_id.lstrip('+').replace('@c.us', '')
        if has_media and normalized_chat_id in main_contacts:
            send_message(chat_id, "I'm sorry, but I couldn't understand your message. Could you please type it clearly and resend it?\n\n_Replied by *ZEUS AI BOT* ✨")
            return "OK", 200
    except Exception as e:
        logger.error(f"Error checking media: {e}")

    response = process_message(chat_id, message_body)
    return response or ("OK", 200)

@app.route(f"/instance/{INSTANCE_ID}", methods=['POST'])
def webhook_handler():
    """Main webhook handler"""
    try:
        data = request.get_json()
        message_data = data.get("data", {}).get("message", {})
        
        response = main(
            message_id=message_data.get("id", {}).get("_serialized"),
            chat_id=message_data.get("from"),
            message_body=message_data.get("body", ""),
            has_media=message_data.get("hasMedia", False)
        )
        return jsonify({"status": "success", "response": response if response else "OK"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
     app.run(host='0.0.0.0', port=80)