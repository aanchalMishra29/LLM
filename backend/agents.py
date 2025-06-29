from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from pathlib import Path
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai_tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from duckduckgo_search import DDGS
from langchain_community.chat_models import ChatLiteLLM
import uuid
import json
import PyPDF2
import mimetypes
import pandas as pd

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    agent_type: str  
    chat_history: List[ChatMessage] = []
    documents: Optional[List[dict]] = None  

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    agent_used: str

app = FastAPI(
    title="Agentic Chatbot Backend",
    description="Backend API for Agentic Chatbot with CrewAI",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

llm = ChatLiteLLM(
    model="gemini/gemini-2.0-flash", 
    api_key=GEMINI_API_KEY,
    temperature=0.7
)

DOCUMENTS_ROOT_PATH = Path("./downloads").resolve()

@tool("DuckDuckGo Search")
def ddg_search(query: str) -> str:
    """Search the web using DuckDuckGo. Use this tool to find current information, news, and general knowledge."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No search results found."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'N/A')
            body = result.get('body', 'N/A')
            href = result.get('href', 'N/A')
            
            formatted_results.append(
                f"{i}. {title}\n"
                f"   {body}\n"
                f"   Source: {href}\n"
            )
        
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Search failed: {str(e)}"

def create_news_agent():
    """Create News Agent for general news and information"""
    return Agent(
        role='News Researcher',
        goal='Provide accurate and up-to-date news information on various topics',
        backstory="""You are an experienced news researcher and journalist. 
        You excel at finding relevant, current information about news events, 
        trends, and general topics. You always verify information from multiple 
        sources and present it in a clear, engaging manner.""",
        llm=llm,
        tools=[ddg_search],
        verbose=True,
        allow_delegation=False
    )


def create_news_task(query: str):
    """Create task for news agent"""
    return Task(
        description=f"""
        Research and provide comprehensive information about: {query}
        
        Use the DuckDuckGo search tool to find current, relevant information.
        
        Your response should:
        1. Provide accurate, current information
        2. Include relevant details and context
        3. Be well-structured and easy to read
        4. Cite sources when possible
        5. Present information in a conversational, helpful manner
        """,
        expected_output="A comprehensive, well-structured response with current information about the query",
        agent=create_news_agent()
    )

def read_file_content(file_path: Path) -> str:
    """Read file content based on file type"""
    try:
        file_extension = file_path.suffix.lower()
        
        if file_extension in ['.txt', '.md', '.csv']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif file_extension == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        
        elif file_extension == '.pdf':
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text_content = []
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text.strip():
                                text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                        except Exception as e:
                            text_content.append(f"--- Page {page_num + 1} ---\n[Error extracting page: {str(e)}]")
                    
                    if text_content:
                        return "\n\n".join(text_content)
                        
                    else:
                        return f"[PDF FILE] {file_path.name} - No text content could be extracted from this PDF"
                        
            except Exception as e:
                return f"[PDF ERROR] {file_path.name} - Failed to read PDF: {str(e)}"
        elif file_extension in ['.xlsx', '.xls']:
            try:
                excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl' if file_extension == '.xlsx' else 'xlrd')
                
                if not excel_data:
                    return f"[EXCEL FILE] {file_path.name} - No sheets found in Excel file"
                
                formatted_content = []
                formatted_content.append(f"[EXCEL FILE] {file_path.name}")
                formatted_content.append(f"Total sheets found: {len(excel_data)}")
                formatted_content.append("=" * 50)
                
                for sheet_name, df in excel_data.items():
                    formatted_content.append(f"\n--- Sheet: {sheet_name} ---")
                    formatted_content.append(f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
                    
                    if df.empty:
                        formatted_content.append("Sheet is empty")
                        continue
                    
                    formatted_content.append(f"Columns: {', '.join(df.columns.astype(str))}")
                    
                    display_df = df.head(100) if len(df) > 100 else df
                    
                    df_string = display_df.to_string(
                        index=True, 
                        max_rows=100, 
                        max_cols=20,
                        na_rep='',
                        float_format=lambda x: f'{x:.2f}' if pd.notna(x) else ''
                    )
                    
                    formatted_content.append("\nData Preview:")
                    formatted_content.append(df_string)
                    
                    if len(df) > 100:
                        formatted_content.append(f"\n... ({len(df) - 100} more rows not shown)")
                    
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        formatted_content.append(f"\nNumeric columns summary:")
                        stats_df = df[numeric_cols].describe()
                        formatted_content.append(stats_df.to_string())
                    
                    formatted_content.append("\n" + "-" * 40)
                
                return "\n".join(formatted_content)
                
            except Exception as e:
                return f"[EXCEL ERROR] {file_path.name} - Failed to read Excel file: {str(e)}"
        else:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if content.strip():
                        return content
                    else:
                        return f"[BINARY FILE] {file_path.name} - File appears to be binary or empty"
            except:
                return f"[UNKNOWN FILE] {file_path.name} - Could not read file content"
                
    except Exception as e:
        return f"[ERROR] Failed to read {file_path.name}: {str(e)}"

def find_document_in_storage(filename: str) -> Optional[Path]:
    if not DOCUMENTS_ROOT_PATH.exists():
        return None

    exact_path = DOCUMENTS_ROOT_PATH / filename
    if exact_path.exists() and exact_path.is_file():
        return exact_path
    
    for file_path in DOCUMENTS_ROOT_PATH.iterdir():
        if file_path.is_file():
            if filename in file_path.name or file_path.name.endswith(filename):
                return file_path
    return None

def create_document_task(query: str, requested_documents: List[dict[str, str]]):
    """Create task for document agent with specific documents"""
    
    return Task(
        description=f"""
        Answer the following question: {query}
        
        User has requested specific documents: {[doc['filename'] for doc in requested_documents]}
        
        Instructions:
        1. Use the Read Document tool to read the requested document(s)
        2. Analyze the document content to answer the user's question
        3. Provide ONLY the direct answer - no extra details
        4. If the requested document doesn't exist, inform the user clearly
        5. If the document exists but doesn't contain relevant information, mention this
        6. Provide accurate and comprehensive answers based on the document content
        7. Be helpful and conversational in your response
        """,
        expected_output="A direct detailed answer to the query based on the requested document(s), clearly indicating if documents were found and analyzed",
        agent=create_document_agent(requested_documents)
    )

def create_document_agent(requested_documents: List[dict[str, str]]):
    """Create Document Agent for specific document analysis"""
    
    @tool("Read Document")
    def read_document(filename: str) -> str:
        """Read and analyze a specific document from storage."""
        
        file_path = find_document_in_storage(filename)
        
        if not file_path:
            return f"Document '{filename}' not found in storage. Please check the filename and ensure the document has been uploaded."
        
        content = read_file_content(file_path)
        
        return f"""
Document Found: {filename}
Actual File Path: {file_path.name}
File Size: {file_path.stat().st_size} bytes
Content Type: {mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'}

Document Content:
{content}
"""
    
    return Agent(
        role='Document Analyst',
        goal='Analyze specific requested documents and answer questions based on their content',
        backstory="""You are a skilled document analyst. You excel at reading and understanding 
        document content, extracting relevant information, and providing comprehensive answers 
        based on the specific documents requested by users. You focus on the exact documents 
        the user has specified and provide detailed analysis of their content.""",
        llm=llm,  
        tools=[read_document],
        verbose=True,
        allow_delegation=False
    )

def process_document_query(message: str, requested_documents: List[dict[str, str]]):
    """Process a query against specific documents"""
    try:
        if not requested_documents:
            return {
                "error": "No documents specified in the request",
                "message": message
            }
        
        missing_docs = []
        found_docs = []
        
        for doc in requested_documents:
            filename = doc.get('filename', '')
            if not filename:
                continue
                
            file_path = find_document_in_storage(filename)
            if file_path:
                found_docs.append({
                    "requested": filename,
                    "actual": file_path.name,
                    "path": str(file_path)
                })
            else:
                missing_docs.append(filename)
        
        task = create_document_task(message, requested_documents)
        
        return {
            "message": message,
            "requested_documents": [doc['filename'] for doc in requested_documents],
            "found_documents": found_docs,
            "missing_documents": missing_docs,
            "task_created": True,
            "storage_path": str(DOCUMENTS_ROOT_PATH.absolute())
        }
        
    except Exception as e:
        return {
            "error": f"Error processing document query: {str(e)}",
            "message": message,
            "requested_documents": [doc.get('filename', '') for doc in requested_documents]
        }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if request.agent_type == "Generic News Agent":
            task = create_news_task(request.message)
            crew = Crew(
                agents=[create_news_agent()],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            response_text = str(result)
            
        elif request.agent_type == "Doc Chat Agent":
            task = create_document_task(request.message, request.documents)
            crew = Crew(
                agents=[create_document_agent(request.documents)],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            response_text = str(result)
            
        else:
            raise HTTPException(status_code=400, detail="Invalid agent type")
        
        return ChatResponse(
            response=response_text,
            timestamp=timestamp,
            agent_used=request.agent_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/process-documents")
async def process_documents(files: List[UploadFile] = File(...)):
    """Process documents, store them in root path, and return their content for immediate use"""
    try:
        DOCUMENTS_ROOT_PATH.mkdir(exist_ok=True)
        
        processed_docs = []
        
        for file in files:
            content = await file.read()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_extension = Path(file.filename).suffix
            stored_filename = f"{timestamp}_{unique_id}_{Path(file.filename).stem}{file_extension}"
            
            file_path = DOCUMENTS_ROOT_PATH / stored_filename
            
            with open(file_path, 'wb') as f:
                f.write(content)

            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            
            if file_ext in ['txt', 'md', 'csv', 'json']:
                text_content = content.decode('utf-8', errors='ignore')
            elif file_ext in ['xlsx', 'xls']:
                text_content = f"[EXCEL] {file.filename} - Excel file uploaded successfully. Use Read Document tool to analyze content."
            else:
                text_content = f"[{file.content_type}] {file.filename} - Content stored at {file_path}"
            
            processed_docs.append({
                "original_filename": file.filename,
                "stored_filename": stored_filename,
                "file_path": str(file_path),
                "relative_path": str(file_path.relative_to(Path.cwd())),
                "content": text_content,
                "size": len(content),
                "content_type": file.content_type
            })
        
        return {
            "message": f"Successfully processed and stored {len(processed_docs)} documents",
            "documents": processed_docs,
            "storage_path": str(DOCUMENTS_ROOT_PATH.absolute())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Backend is running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "agents:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )