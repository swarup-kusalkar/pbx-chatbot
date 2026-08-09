# PBX Support Chatbot

A RAG-based chatbot designed to assist engineers and support staff with PBX (Private Branch Exchange), VoIP, IVR, SIP trunking, Asterisk, and contact center technologies. The chatbot provides accurate, technical answers by retrieving information from a curated knowledge base and using large language models for response generation.

## Features

- **Retrieval-Augmented Generation (RAG)**: Combines semantic search with LLMs to provide accurate, context-aware answers
- **Dual LLM Support**: Primary Groq (Llama 3) with Gemini fallback for reliability
- **Knowledge Base**: Curated articles covering PBX systems, VoIP, SIP trunks, IVR systems, Asterisk, and more
- **Conversation Context Management**: Automatic summarization to maintain context in long conversations
- **Session Management**: Create, list, delete, and export chat sessions
- **Article Browser**: Browse and read knowledge base articles directly in the UI
- **Responsive UI**: Modern interface with sidebar for sessions/articles and main chat area
- **Export Functionality**: Download chat conversations as text files
- **Quick Start Questions**: Predefined questions to help users get started

## Architecture

```
+---------------------+    +---------------------+    +---------------------+
|   Frontend UI       |    |   FastAPI Server    |    |   Knowledge Base    |
|  (HTML/CSS/JS)      |<-->|  (Python/API)       |<-->| (MySQL + ChromaDB)  |
+---------------------+    +---------------------+    +---------------------+
                                   |
                                   v
                         +---------------------+
                         |   LLM Providers     |
                         | (Groq/Gemini API)   |
                         +---------------------+
```

### Core Components

1. **Backend Server** (`server.py`): FastAPI application handling API requests
2. **Database Layer**: SQLAlchemy models for sessions, messages, and knowledge base
3. **Vector Store**: ChromaDB for semantic search of knowledge base articles
4. **LLM Clients**: Groq and Gemini API integrations with automatic fallback
5. **Prompt Engineering**: System prompts and context building for accurate responses
6. **Conversation Compression**: Automatic summarization to manage token usage
7. **Frontend UI**: Vanilla JavaScript application with marked.js for markdown rendering

## Knowledge Base

The chatbot's knowledge base consists of markdown articles covering:

- **IVR Systems**: Overview, types, components, design best practices, CRM integration
- **SIP Trunking**: SIP protocol, VoIP codecs, architecture, components, benefits
- **Asterisk**: PBX platform information (referenced in articles)
- **Call Queues**: Contact center queue management
- **Voicemail Systems**: Configuration and management
- **DTMF**: Dual-tone multi-frequency signaling
- **ARI**: Asterisk REST Interface
- **Call Recording**: Recording technologies and compliance
- **STT/TTS**: Speech-to-text and text-to-speech technologies

Articles are stored in both MySQL (for metadata) and ChromaDB (for semantic search).

## Technical Details

### Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- SQLAlchemy: ORM for MySQL
- PyMySQL: MySQL driver
- ChromaDB: Vector database
- Sentence Transformers: Text embeddings
- Python-dotenv: Environment variable management
- Pydantic: Data validation
- Httpx: HTTP client for LLM APIs

### Environment Variables

Create a `.env` file with:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_MODEL=gemini-3-flash-preview
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=pbx_chatbot
APP_PORT=3000
CHROMA_PERSIST_PATH=./chroma_store
MAX_HISTORY_MESSAGES=10
SUMMARY_TRIGGER_COUNT=10
RECENT_MESSAGES_AFTER_SUMMARY=6
```

> **Security Note**: Never commit your actual `.env` file to public repositories. Add it to your `.gitignore` file to keep API keys and database credentials secure.

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pbx-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file using the variables shown above, or copy `.env.example` if it exists.
   # Edit .env with your API keys and database credentials
   ```

5. **Initialize the knowledge base**
   ```bash
   python scripts/seed_kb.py
   ```

6. **Start the server**
   ```bash
   python server.py
   ```
   Or with reload during development:
   ```bash
   uvicorn server:app --reload
   ```

7. **Access the application**
   Open your browser to `http://localhost:3000`

## API Endpoints

### Chat
- `POST /api/chat` - Send a message and get a response
  - Body: `{ "message": "string", "session_id": "string (optional)" }`
  - Returns: Chat response with reply, session ID, retrieved topics, LLM used

### Sessions
- `GET /api/sessions` - List all chat sessions
- `POST /api/sessions` - Create a new session
  - Body: `{ "session_id": "string (optional)" }`
- `GET /api/history/{session_id}` - Get chat history for a session
- `DELETE /api/sessions/{session_id}` - Delete a session

### Knowledge Base
- `GET /api/knowledge` - Get all knowledge base articles
- `GET /api/export/{session_id}` - Export chat session as text file

## How It Works

1. **User Query**: User sends a message through the UI
2. **Context Retrieval**: System retrieves relevant knowledge base chunks using semantic search
3. **Conversation Context**: Previous conversation history (or summary) is included
4. **Prompt Construction**: System prompt + knowledge base + history + user query
5. **LLM Generation**: Request sent to Groq (primary) or Gemini (fallback)
6. **Response Delivery**: Answer returned to user with sources and metadata
7. **Conversation Management**: Long conversations are automatically summarized to maintain context while reducing token usage

## Design Decisions

### Why RAG?
- Reduces hallucinations by grounding responses in factual knowledge base
- Provides source attribution for transparency
- Allows knowledge base updates without retraining models
- Cost-effective compared to fine-tuning large models

### Dual LLM Strategy
- Primary: Groq for fast inference with Llama 3
- Fallback: Gemini for reliability if Groq is unavailable
- Automatic failover ensures continuous service

### Conversation Summarization
- Triggered after configurable number of messages
- Preserves essential context while managing token limits
- Uses the same LLMs for summarization consistency

### Knowledge Base Chunking
- Articles split into semantic chunks for better retrieval
- Each chunk includes metadata (topic, section, question)
- Enables precise retrieval of relevant information

## Future Enhancements

- User authentication and role-based access
- Multi-language support
- Integration with ticketing systems
- Voice input/output capabilities
- Analytics dashboard for usage patterns
- Custom knowledge base upload capability
- Docker containerization for easy deployment

## Troubleshooting

### Common Issues

1. **LLM API Errors**
   - Check API keys in `.env`
   - Verify API keys have sufficient quota/credits
   - Ensure internet connectivity to API endpoints

2. **Database Connection Issues**
   - Verify MySQL server is running
   - Check MySQL credentials in `.env`
   - Ensure database exists (`pbx_chatbot`)

3. **ChromaDB Initialization**
   - First run may take time as vector database is initialized
   - Check `./chroma_store` directory for data files
   - Delete directory to reset (will trigger re-seeding)

4. **Port Conflicts**
   - Change `APP_PORT` in `.env` if port 3000 is in use
   - Update any hardcoded port references if needed

## License

This project is licensed under the MIT License.

## Acknowledgments

- Groq for fast LLM inference
- Google for Gemini API
- The open-source community for FastAPI, ChromaDB, and other libraries
- Telecom professionals and documentation sources that informed the knowledge base