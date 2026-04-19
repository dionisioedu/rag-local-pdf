import gradio as gr
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os

# ===================== CONFIGURAÇÃO =====================
PERSIST_DIR = "./chroma_db"
PDF_FOLDER = "./pdfs"

embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(model="llama3.2", temperature=0.3)

# Template de prompt em português
prompt_template = """Você é um assistente útil e preciso.
Responda APENAS com base no contexto abaixo. Se não souber, diga "Não tenho informação suficiente".

Contexto:
{context}

Pergunta: {question}

Resposta:"""

prompt = ChatPromptTemplate.from_template(prompt_template)

# ===================== INDEXAÇÃO =====================
if not os.path.exists(PERSIST_DIR) or len(os.listdir(PDF_FOLDER)) > 0:
    print("📄 Indexando PDFs pela primeira vez...")
    loader = PyPDFDirectoryLoader(PDF_FOLDER)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    print(f"✅ {len(splits)} chunks indexados!")
else:
    vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    print("✅ Banco de vetores já existe.")

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# ===================== CHAIN RAG =====================
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ===================== INTERFACE =====================
def chat(message, history):
    response = rag_chain.invoke(message)
    return response

with gr.Blocks(title="🤖 Minha IA Local - Chat com PDFs", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 RAG Local com PDFs\nPergunte qualquer coisa sobre os PDFs da pasta `./pdfs`")
    
    chatbot = gr.ChatInterface(
        fn=chat,
        title="Chat com seus documentos",
        description="Tudo roda na sua máquina. Privado e grátis.",
        examples=[
            "Qual é o principal ponto do documento?",
            "Resuma o texto em 3 frases",
            "O que diz sobre [tópico do seu PDF]?"
        ]
    )

if __name__ == "__main__":
    demo.launch(share=False)