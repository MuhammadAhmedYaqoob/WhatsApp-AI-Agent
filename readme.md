# 🤖 Zeus WhatsApp AI Bot

Zeus is an AI-powered WhatsApp chatbot built with Flask and integrated through [waapi.app](https://waapi.app). It generates intelligent responses using OpenAI GPT and can fetch reply data from Google Sheets, WordPress, and local template files. The bot runs locally and communicates with WhatsApp via webhook using ngrok.

---

## 🧾 Requirements

- A subscription on [waapi.app](https://waapi.app)
- Instance ID and API Token from your waapi.app dashboard
- OpenAI API Key
- Google Service Account JSON for accessing Google Sheets
- Python 3.7 or above
- ngrok (for exposing localhost to the internet)

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/MuhammadAhmedYaqoob/WhatsApp-AI-Agent.git
cd WhatsApp-AI-Agent 
```

### 2. Configure Environment Variables
Create a .env file in the root directory and add the following:

- INSTANCE_ID=your_instance_id_from_waapi
- WAPI_TOKEN=your_api_token_from_waapi
- OPENAI_API_KEY=your_openai_key
- GOOGLE_SHEET_ID=your_google_sheet_id
- GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service_account.json

### 3. Run ngrok to Expose Flask Webhook

```bash
ngrok http 80
```

Copy the generated https://xxxxx.ngrok.io URL and paste it into your waapi.app webhook settings under Webhook URL.

### 4. Start the Flask Bot

```bash
python app.py
```
Your server will now be running on:
http://localhost:80


## 🧠 How It Works

### 📬 Message Flow

- A user sends a WhatsApp message.
- waapi.app forwards the message to your Flask webhook via ngrok.
- Flask receives it and processes the message using routing logic.

- 🤖 Response Generation
The bot chooses how to respond based on:

💬 OpenAI GPT for dynamic AI-powered replies
📊 Google Sheets for predefined templates or logs
🌐 WordPress integration (optional)
📁 Local template files for static responses

🔀 Smart Routing
Functions like check_zeus_inquery() and check_troubleshoot_inquery() analyze the message content to determine the best response source.

### 📁 Project Structure
.
├── app.py                  # Flask server with webhook logic
├── bot.py                  # Core logic for AI responses
├── utils.py                # Helpers: routing, sending, matching
├── templates/              # Local static templates (optional)
├── .env                    # Environment variables (excluded from git)
├── requirements.txt        # Python dependencies
└── README.md               # This file

### 🛠 Features

✅ WhatsApp integration via waapi.app
✅ GPT-powered replies using OpenAI API
✅ Google Sheets integration for response templates
✅ Local static reply support (JSON/text)
✅ Optional WordPress content integration
✅ Modular codebase for easy customization
✅ Runs locally on port 80 with public access via ngrok

