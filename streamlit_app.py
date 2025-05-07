import streamlit as st
import openai
import tempfile
import os
from PyPDF2 import PdfReader

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]  # secrets에 키 등록 필요

st.set_page_config(page_title="ChatPDF", layout="wide")

# 앱에서 사용할 세션 데이터 초기화
if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []

openai.api_key = OPENAI_API_KEY

def extract_pdf_text(file):
    # PDF에서 텍스트 추출
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def upload_pdf_to_openai(file_path):
    # OpenAI에 파일 업로드 (File Search 준비)
    file_obj = openai.files.create(
        file=open(file_path, "rb"), 
        purpose="assistants"
    )
    return file_obj.id

def delete_openai_file(file_id):
    # OpenAI 파일 삭제(벡터스토어 삭제)
    openai.files.delete(file_id)

def find_latest_file_id():
    # 가장 최근 파일 id조회 (혹시 모를 상황 대비)
    files = openai.files.list()
    files = sorted(files.data, key=lambda x: x.created_at, reverse=True)
    for f in files:
        if f.purpose == "assistants":
            return f.id
    return None

def chat_with_file(prompt, file_id):
    # File Search + GPT와 대화하는 함수 (OpenAI Assistants)
    # Assistant 임시 생성
    assistant = openai.beta.assistants.create(
        instructions="너는 사용자가 올린 PDF 내용에 충실히 답하는 도움말 챗봇이야.",
        model="gpt-4-turbo",
        tools=[{"type": "file_search"}],
        file_ids=[file_id]
    )
    thread = openai.beta.threads.create()
    message = openai.beta.threads.messages.create(
        thread_id=thread.id, 
        role="user",
        content=prompt
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread.id, 
        assistant_id=assistant.id
    )
    import time
    # 답변 대기
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)
    # 답변 추출
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value

####
# UI
####
st.title("📄 ChatPDF")

st.write("Streamlit file uploader를 통해 PDF를 업로드 후, PDF 내용을 이용해 대화해보세요.")

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

# Clear 버튼
col1, col2 = st.columns([1,4])
with col1:
    if st.button("Clear 파일/세션"):
        # 세션정보, 벡터스토어 삭제
        if st.session_state.uploaded_file_id:
            delete_openai_file(st.session_state.uploaded_file_id)
        st.session_state.uploaded_file_id = None
        st.session_state.conversation = []
        st.success("업로드한 파일 및 세션이 초기화 되었습니다!")
        st.experimental_rerun()

if uploaded_file is not None and st.session_state.uploaded_file_id is None:
    # 파일 임시저장 > openai 업로드
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    st.session_state.pdf_text = extract_pdf_text(tmp_path)
    file_id = upload_pdf_to_openai(tmp_path)
    st.session_state.uploaded_file_id = file_id
    os.remove(tmp_path)
    st.success("파일 업로드 성공 및 인덱싱 완료! 질문을 입력해보세요.")

if st.session_state.uploaded_file_id:
    st.text_area("PDF 미리보기", value=st.session_state.pdf_text[:1000], height=200)

    if len(st.session_state.conversation) > 0:
        for role, msg in st.session_state.conversation:
            with st.chat_message(role):
                st.markdown(msg)

    user_input = st.chat_input("PDF에 대해 궁금한 점을 입력하세요...")
    if user_input:
        # 챗봇과 대화
        st.session_state.conversation.append(("user", user_input))
        with st.spinner("답변 생성 중..."):
            bot_resp = chat_with_file(user_input, st.session_state.uploaded_file_id)
        st.session_state.conversation.append(("assistant", bot_resp))
        st.experimental_rerun()
else:
    st.info("먼저 PDF 파일을 업로드하세요.")
