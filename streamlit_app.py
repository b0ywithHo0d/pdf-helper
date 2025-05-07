import streamlit as st
import openai
import tempfile
import os
from PyPDF2 import PdfReader

st.set_page_config(page_title="ChatPDF", layout="wide")

# 1. 세션 데이터 초기화
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""
if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# 2. PDF에서 텍스트 추출
def extract_pdf_text(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text

# 3. PDF를 OpenAI에 업로드
def upload_pdf_to_openai(file_path, api_key):
    openai.api_key = api_key
    file_obj = openai.files.create(
        file=open(file_path, "rb"),
        purpose="assistants"
    )
    return file_obj.id

# 4. OpenAI 파일 삭제
def delete_openai_file(file_id, api_key):
    openai.api_key = api_key
    try:
        openai.files.delete(file_id)
    except Exception:
        pass  # 이미 삭제된 파일 대비 예외처리

# 5. OpenAI Assistant API로 질의하기 (gpt-4o)
def chat_with_file(prompt, file_id, api_key):
    openai.api_key = api_key
    assistant = openai.beta.assistants.create(
        instructions="너는 사용자가 올린 PDF 내용에 충실히 답하는 도움말 챗봇이야.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
        file_ids=[file_id]
    )
    thread = openai.beta.threads.create()
    # User 메시지 등록
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )
    # Run Assistant
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    import time
    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id
        )
        if run_status.status == "completed":
            break
        time.sleep(1)
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value

# ------------------------------- UI -------------------------------

st.title("📄 ChatPDF")
st.write("PDF를 올리고, 업로드한 파일 내용만으로 대화해보세요.")

# OpenAI API Key 입력 (비밀번호 스타일)
api_key = st.text_input(
    "OpenAI API 키를 입력하세요:",
    type="password",
    placeholder="sk-로 시작하는 개인 키를 입력",
    value=st.session_state.openai_api_key,
)
if api_key:
    st.session_state.openai_api_key = api_key

if not st.session_state.openai_api_key:
    st.warning("OpenAI API 키를 입력해야 서비스를 이용할 수 있습니다.")
    st.stop()

# PDF 업로더 (1개)
uploaded_file = st.file_uploader("PDF 파일 업로드", type=["pdf"])

# Clear 버튼 (파일 및 대화 내역 삭제)
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("Clear 파일/세션"):
        if st.session_state.uploaded_file_id:
            delete_openai_file(st.session_state.uploaded_file_id, st.session_state.openai_api_key)
        st.session_state.uploaded_file_id = None
        st.session_state.conversation = []
        st.session_state.pdf_text = ""
        st.success("업로드한 파일 및 대화 세션이 초기화 되었습니다!")
        st.rerun()

# 새 PDF 업로드시 flow
if uploaded_file is not None and st.session_state.uploaded_file_id is None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    st.session_state.pdf_text = extract_pdf_text(tmp_path)
    try:
        file_id = upload_pdf_to_openai(tmp_path, st.session_state.openai_api_key)
    finally:
        os.remove(tmp_path)
    st.session_state.uploaded_file_id = file_id
    st.success("파일 업로드 성공 및 인덱싱 완료! 질문을 입력해보세요.")
    st.rerun()

# PDF 업로드 후 UI
if st.session_state.uploaded_file_id:
    st.text_area("PDF 미리보기", value=st.session_state.pdf_text[:1000], height=200)

    # 대화 기록 출력
    if len(st.session_state.conversation) > 0:
        for role, msg in st.session_state.conversation:
            with st.chat_message(role):
                st.markdown(msg)

    user_input = st.chat_input("PDF에 대해 궁금한 점을 입력하세요...")
    if user_input:
        st.session_state.conversation.append(("user", user_input))
        with st.spinner("답변 생성 중..."):
            try:
                bot_resp = chat_with_file(
                    user_input,
                    st.session_state.uploaded_file_id,
                    st.session_state.openai_api_key
                )
            except Exception as e:
                bot_resp = f"오류가 발생했습니다: {e}"
        st.session_state.conversation.append(("assistant", bot_resp))
        st.rerun()
else:
    st.info("먼저 PDF 파일을 업로드하세요.")
