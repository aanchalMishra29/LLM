# 🤖 Agentic AI Application

A powerful multi-agent system that combines news intelligence and document analysis capabilities. This application leverages specialized AI agents to provide real-time news information and answer questions from uploaded documents.

## 🌟 Features

### 📰 Generic News Agent
- **Real-time News Retrieval**: Get current news and information using DuckDuckGo search
- **Intelligent Analysis**: AI-powered news analysis and summarization
- **Current Events**: Stay updated with latest happenings across various domains

### 📄 Document Chat Agent
- **Multi-format Support**: Process PDF, Excel (.xlsx/.xls), text, JSON, CSV
- **Intelligent Q&A**: Ask questions about your uploaded documents
- **Data Extraction**: Extract specific information from complex documents
- **Concise Responses**: Get direct answers without unnecessary details

## 🛠️ Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| PDF | `.pdf` | Text extraction from PDF documents |
| Excel | `.xlsx`, `.xls` | Spreadsheet data analysis |
| Text | `.txt`, `.md` | Plain text and Markdown files |
| JSON | `.json` | Structured data files |
| CSV | `.csv` | Comma-separated values |

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-ai-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt

### Running the Application

```bash
# Start the FastAPI server
python agents.py

# Or use uvicorn directly
uvicorn agents:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at `http://localhost:8000`

## 📖 API Usage

### Health Check
```bash
GET /health
```

### News Agent
```bash
POST /chat
Content-Type: application/json

{
  "message": "What's the latest news about AI technology?",
  "agent_type": "Generic News Agent",
  "documents": []
}
```

### Document Agent
```bash
POST /chat
Content-Type: application/json

{
  "message": "Your Prompt",
  "agent_type": "Doc Chat Agent",
  "documents": [{"filename": "dummy.xlsx"}],
  "concise_mode": true
}
```

### Document Upload
```bash
POST /process-documents
Content-Type: multipart/form-data

# Upload files using form data
```

## 💡 Usage Examples

### 1. News Queries
```json
{
  "message": "Recent developments in renewable energy",
  "agent_type": "Generic News Agent"
}
```

### 2. Document Analysis
```json
{
  "message": "Show me sales data for Q1 2024",
  "agent_type": "Doc Chat Agent",
  "documents": [{"filename": "sales_report.xlsx"}]
}
```

### 3. Specific Information Extraction
```json
{
  "message": "Find customer contact details for ABC Corp",
  "agent_type": "Doc Chat Agent",
  "documents": [{"filename": "customer_database.csv"}],
  "concise_mode": true
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Set custom document storage path
DOCUMENTS_ROOT_PATH=/path/to/documents

# Optional: Configure LLM settings
LLM_MODEL=your_preferred_model
```

### Document Storage
- Documents are automatically stored in the `documents/` directory
- Unique filenames are generated to prevent conflicts
- Supports concurrent file uploads

## 🏗️ Architecture

```
┌─────────────────────┐
│   FastAPI Server    │
├─────────────────────┤
│  📰 News Agent      │
│  • DuckDuckGo Search│
│  • News Analysis    │
├─────────────────────┤
│  📄 Document Agent  │
│  • File Processing  │
│  • Content Analysis │
│  • Q&A System      │
└─────────────────────┘
```

### Agent Capabilities

#### News Agent
- Web search using DuckDuckGo
- Real-time information retrieval
- Content summarization
- Current events analysis

#### Document Agent
- Multi-format file reading
- Intelligent content extraction
- Context-aware question answering
- Data analysis and insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

**Built with ❤️ using CrewAI and FastAPI**