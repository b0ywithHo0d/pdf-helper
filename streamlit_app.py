import streamlit as st
import openai
import fitz  # PyMuPDF
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
import tempfile
import os

st.set_page_config(page_title="ChatPDF", layout="centered")
st.title("📄 ChatPDF: PDF와 대화하기")

# 🔑 API 키 입력
api_key = st.secrets.get("openai_api_key") or st.text_input("🔑 OpenAI API 키를 입력하세요", type="password")
if api_key:
    openai.api_key = api_key
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

uploaded_file = st.file_uploader("PDF 파일 업로드", type="pdf")
clear = st.button("🧹 Clear")

if clear:
    st.session_state.clear()
    st.success("상태가 초기화되었습니다. 새 PDF를 업로드하세요.")

# 텍스트 추출 함수
def extract_text_from_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

# PDF 업로드 후 처리
if uploaded_file and "vectorstore" not in st.session_state:
    text = extract_text_from_pdf(uploaded_file)
    docs = [Document(page_content=text)]
    st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
    st.success("📚 PDF 벡터 저장소 생성 완료!")

# 사용자 입력 → 검색 + GPT 응답
user_input = st.text_input("질문을 입력하세요:")

if user_input and "vectorstore" in st.session_state:
    relevant_docs = st.session_state.vectorstore.similarity_search(user_input, k=3)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    prompt = f"""
다음은 사용자가 업로드한 PDF 내용 일부입니다. 이 내용을 바탕으로 질문에 답변하세요.
PDF 내용:
\"\"\"
{context}
\"\"\"

사용자 질문:
{user_input}
"""

    with st.spinner("GPT가 답변을 생성 중입니다..."):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 PDF 문서 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        st.success(response.choices[0].message.content)
