import streamlit as st
import openai
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document

st.set_page_config(page_title="ChatPDF", layout="centered")
st.title("📄 ChatPDF: RAG 기반 PDF 챗봇")

# 🔑 OpenAI API 키 입력
api_key = st.secrets.get("openai_api_key")
if not api_key:
    api_key = st.text_input("🔐 OpenAI API 키를 입력하세요", type="password")
    if not api_key:
        st.warning("OpenAI API 키가 필요합니다.")
        st.stop()

openai.api_key = api_key
embeddings = OpenAIEmbeddings(openai_api_key=api_key)

# 📎 PDF 파일 업로드
uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")

# 🧹 상태 초기화 버튼
if st.button("🧹 Clear"):
    st.session_state.clear()
    st.success("세션이 초기화되었습니다. PDF를 다시 업로드하세요.")

# 📄 PDF → 텍스트 → 문서 리스트
def extract_docs_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    docs = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text and text.strip():
            docs.append(Document(page_content=text))
    return docs

# 🔍 벡터 저장소 생성
if uploaded_file and "vectorstore" not in st.session_state:
    with st.spinner("📖 PDF 분석 중..."):
        docs = extract_docs_from_pdf(uploaded_file)
        st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
        st.success("✅ 벡터 저장소 생성 완료!")

# 🙋 사용자 질문 입력
query = st.text_input("💬 질문을 입력하세요:")

# 🤖 RAG 질의응답
if query and "vectorstore" in st.session_state:
    with st.spinner("🔍 문서 검색 중..."):
        docs = st.session_state.vectorstore.similarity_search(query, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""
다음은 사용자가 업로드한 PDF 문서의 일부입니다. 이를 참고해 질문에 답변하세요.

📄 문서 내용:
\"\"\"
{context}
\"\"\"

🙋 사용자 질문:
{query}
"""

    with st.spinner("🤖 GPT가 답변을 생성 중입니다..."):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 PDF 문서 분석에 능한 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        st.markdown("### 🧠 GPT 응답")
        st.write(response.choices[0].message.content)
