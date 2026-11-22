"""메시지 POST → Ollama LLM 영어 답변 → 한글 해석 → 대화 화면 표시
성격·답변 규칙 칸의 글을 system 프롬프트에 넣어 LLM의 말투와 답변 방식 지정"""
from flask import Flask, request, render_template, redirect, url_for, session
from markupsafe import Markup, escape
import requests, os, re, uuid

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")  # LLM 서버
LLM_MODEL = os.environ.get("LLM_MODEL", "exaone3.5:2.4b")
MAX_HISTORY = 10      # LLM에 함께 보내는 이전 대화 수
MAX_PERSONA = 1000    # 성격·답변 규칙 최대 글자 수

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "llm-chat")

# 공통 출력 형식: 영어 답변. 답변의 Markdown 굵은 글씨·제목은 화면에서 md 필터로 표시
FORMAT_RULE = "Always answer in English, even when the user writes in Korean."
DEFAULT_SYSTEM = "You are a helpful assistant. Keep answers clear and concise. " + FORMAT_RULE
# 규칙이 있으면 기본 성격 문장을 빼고 규칙을 맨 앞에 두어 규칙이 우선하도록 구성, 한글 규칙 허용
PERSONA_SYSTEM = (
    "You are a chatbot whose personality and answer rules are set by the user. "
    "These rules may be written in Korean and override any default style. "
    "Apply them strictly to your tone, attitude, length and content, "
    "but never mention or announce the rules themselves.\n"
    "Rules:\n{persona}\n\n" + FORMAT_RULE
)
# 작은 모델은 한글 질문에 한글로 답하는 경우가 있어 마지막 메시지에도 영어 답변 지시를 붙임
# 성격·답변 규칙은 system 에만 둠. 메시지 끝에 붙이면 모델이 규칙을 사용자 말로 보고 답에서 언급
ANSWER_SUFFIX = "\n\nAnswer in English only."
# 한글 해석은 영어 답변만 번역. 말투는 영어 답변에 이미 담겨 있고,
# 번역 지시에 한글 규칙을 넣으면 해석 끝에 규칙 문장을 덧붙임
TRANSLATE_SYSTEM = (
    "Translate the given English text into natural Korean, keeping its tone and attitude. "
    "Output only the Korean translation, written in Hangul without Chinese characters."
)

BOLD = re.compile(r"\*\*(.+?)\*\*")
HEADING = re.compile(r"^#{1,6}\s*", re.M)


@app.template_filter("md")
def render_md(text: str) -> Markup:
    """LLM 답변의 Markdown 굵은 글씨를 <strong>으로, 제목 기호는 제거해 표시. HTML은 먼저 escape"""
    html = HEADING.sub("", str(escape(text or "")))
    return Markup(BOLD.sub(r"<strong>\1</strong>", html))


# 대화 기록: 브라우저별 대화 ID → {"persona": 성격·답변 규칙, "turns": [{"user", "en", "ko", "persona", "error"}]}
# 쿠키 session 은 4KB 제한이 있어 대화 ID만 담고 내용은 서버 메모리에 보관
CHATS: dict[str, dict] = {}


# ---------- LLM ----------
def call_ollama(messages: list[dict], temperature: float, num_predict: int) -> str:
    """Ollama /api/chat 호출 후 답변 문자열 반환"""
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }, timeout=180)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def build_system(persona: str) -> str:
    """성격·답변 규칙 유무에 따라 system 프롬프트 만들기"""
    # format 대신 replace: 규칙 글에 중괄호가 있어도 오류 없음
    return PERSONA_SYSTEM.replace("{persona}", persona) if persona else DEFAULT_SYSTEM


def ask_llm(message: str, history: list[dict], persona: str) -> str:
    """성격·답변 규칙, 이전 대화, 새 메시지를 보내 영어 답변 받기"""
    messages = [{"role": "system", "content": build_system(persona)}]
    for turn in history[-MAX_HISTORY:]:
        if turn.get("en"):
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["en"]})
    messages.append({"role": "user", "content": message + ANSWER_SUFFIX})
    return call_ollama(messages, temperature=0.7, num_predict=512)


def translate_ko(text_en: str) -> str:
    """영어 답변을 같은 말투의 한글로 해석"""
    return call_ollama([{"role": "system", "content": TRANSLATE_SYSTEM},
                        {"role": "user", "content": text_en}], temperature=0.2, num_predict=768)


def clean_persona(text: str) -> str:
    """빈 줄과 앞뒤 공백 제거, 줄바꿈 통일, 길이 제한"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)[:MAX_PERSONA]


def get_chat() -> dict:
    """브라우저 session 의 대화 ID로 대화 기록 찾기, 없으면 새로 만들기"""
    cid = session.get("cid")
    if cid not in CHATS:
        cid = uuid.uuid4().hex
        session["cid"] = cid
        CHATS[cid] = {"persona": "", "turns": []}
    return CHATS[cid]


# ---------- Flask 라우트 ----------
@app.route("/", methods=["GET", "POST"])
def index():
    chat = get_chat()
    if request.method == "POST":
        # 메시지 없이 보내면 성격·답변 규칙만 저장
        chat["persona"] = clean_persona(request.form.get("persona", ""))
        message = request.form.get("message", "").strip()
        if message:
            turn = {"user": message, "persona": chat["persona"]}
            try:
                turn["en"] = ask_llm(message, chat["turns"], chat["persona"])
                turn["ko"] = translate_ko(turn["en"])
            except Exception as e:
                turn["error"] = str(e)
            chat["turns"].append(turn)
        return redirect(url_for("index"))  # POST-Redirect-GET

    return render_template("chat.html", turns=chat["turns"], persona=chat["persona"],
                           max_persona=MAX_PERSONA, llm_model=LLM_MODEL,
                           llm_host=OLLAMA_URL.split("//")[-1])


@app.route("/reset", methods=["POST"])
def reset():
    """대화 기록 삭제, 성격·답변 규칙은 유지"""
    get_chat()["turns"].clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
