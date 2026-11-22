# Flask → LangChain 구조화 JSON 번역 → ComfyUI 이미지 생성
from flask import Flask, request, render_template, Response, abort
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import requests, json, time, os, random

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")  # LLM 서버
COMFY_URL = os.environ.get("COMFY_URL", "http://host.docker.internal:8188")     # 이미지 생성 서버
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = os.path.join(BASE_DIR, "static", "workflow.json")  # SDXL Turbo 워크플로

app = Flask(__name__)


# ---- 구조화 출력 형식: 이 4개 키를 가진 JSON ----
class PromptPair(BaseModel):
    original_pos: str = Field(description="입력한 positive 프롬프트를 번역하지 않고 입력 언어 그대로 복사한 원문")
    original_neg: str = Field(description="입력한 negative 프롬프트를 번역하지 않고 그대로 복사한 원문, 없으면 빈 문자열")
    trans_pos: str = Field(description="original_pos를 이미지 생성용 영어 프롬프트로 번역한 것, 쉼표로 구분한 영어 키워드")
    trans_neg: str = Field(description="original_neg를 영어로 번역한 것, 없으면 빈 문자열")


# ---- 체인 구성 (서버 시작 시 1회 초기화) ----
# keep_alive=0: 번역 후 LLM을 GPU 메모리에서 내려 ComfyUI가 GPU를 쓸 수 있게 함
_json_llm = ChatOllama(model="gemma3:4b", temperature=0.2, base_url=OLLAMA_URL, keep_alive=0)
_json_parser = JsonOutputParser(pydantic_object=PromptPair)
_json_format = _json_parser.get_format_instructions()

_json_prompt = ChatPromptTemplate.from_template(
    """다음 이미지 생성 프롬프트를 JSON으로 정리해.
- "original_pos": 아래 positive 원문을 번역하지 말고 한 글자도 바꾸지 않고 그대로 복사
- "original_neg": 아래 negative 원문을 번역하지 말고 그대로 복사, 비어 있으면 ""
- "trans_pos": positive 원문을 Stable Diffusion용 영어 프롬프트로 번역, 쉼표로 구분한 영어 키워드
- "trans_neg": negative 원문을 영어로 번역, 비어 있으면 ""
반드시 JSON만 출력.
{format_instructions}
positive:
{pos}
negative:
{neg}
"""
)
_json_chain = _json_prompt | _json_llm | _json_parser
# ---------------------------------------------


def translate_prompts(pos: str, neg: str) -> dict:
    """LangChain 체인으로 원문·번역문 JSON 받기"""
    return _json_chain.invoke({"pos": pos, "neg": neg, "format_instructions": _json_format})


# ---------- ComfyUI 기능별 함수 ----------
def load_workflow(path: str) -> dict:
    """JSON 워크플로를 파일에서 읽기"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_prompts(graph: dict, pos: str, neg: str,
                   pos_node_id: str = "6", neg_node_id: str = "7", seed_node_id: str = "13") -> dict:
    """번역된 영어 프롬프트를 positive·negative 노드에 넣고 seed 변경"""
    graph[seed_node_id]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
    graph[pos_node_id]["inputs"]["text"] = pos
    graph[neg_node_id]["inputs"]["text"] = neg
    return graph


def submit_prompt(graph: dict) -> str:
    """ComfyUI /prompt 에 워크플로 제출 후 prompt_id 반환"""
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": graph}, timeout=30)
    r.raise_for_status()
    return r.json()["prompt_id"]


def poll_history(prompt_id: str, timeout_sec: int = 300, interval: float = 1.0) -> dict | None:
    """/history/{prompt_id} 에서 완료 결과를 받을 때까지 대기"""
    end = time.time() + timeout_sec
    while time.time() < end:
        h = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=30)
        if h.status_code == 200 and h.json():
            return list(h.json().values())[0]
        time.sleep(interval)
    return None


def extract_first_image(history_block: dict) -> dict | None:
    """히스토리 블록에서 SaveImage 출력의 첫 번째 이미지 정보"""
    for node_out in (history_block or {}).get("outputs", {}).values():
        if node_out.get("images"):
            img = node_out["images"][0]
            return {"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")}
    return None


# ---------- Flask 라우트 ----------
@app.route("/", methods=["GET", "POST"])
def index():
    pos = request.form.get("pos", "").strip()
    neg = request.form.get("neg", "").strip()
    result, img_url, error = None, "", ""

    if request.method == "POST" and pos:
        try:
            # 1) LangChain: 원문 → 원문·번역문 JSON
            result = translate_prompts(pos, neg)
            # 2) ComfyUI: JSON의 trans_pos·trans_neg 키 값을 워크플로에 넣어 이미지 생성
            graph = update_prompts(load_workflow(WORKFLOW_PATH), result["trans_pos"], result.get("trans_neg", ""))
            image = extract_first_image(poll_history(submit_prompt(graph)))
            if image is None:
                raise RuntimeError("ComfyUI 응답 시간 초과")
            img_url = "/image?" + requests.compat.urlencode(image)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

    return render_template("index.html", pos=pos, neg=neg, result=result,
                           result_json=json.dumps(result, ensure_ascii=False, indent=2) if result else "",
                           img_url=img_url, error=error,
                           llm_host=OLLAMA_URL.split("//")[-1], comfy_host=COMFY_URL.split("//")[-1])


@app.route("/image")
def image():
    """ComfyUI /view 이미지를 Flask를 거쳐 전달. 브라우저가 ComfyUI 주소에 접속하지 않아도 됨"""
    params = {k: request.args.get(k, "") for k in ("filename", "subfolder", "type")}
    if not params["filename"]:
        abort(404)
    r = requests.get(f"{COMFY_URL}/view", params=params, timeout=30)
    if r.status_code != 200:
        abort(r.status_code)
    return Response(r.content, mimetype=r.headers.get("Content-Type", "image/png"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
