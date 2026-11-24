# app2.py
from flask import Flask, request, render_template
import requests, json, time, os, random
 
COMFY_URL = os.environ.get("COMFY_URL", "http://192.168.24.106:8188")  # GPU Server URL, 환경 변수로 변경 가능
WORKFLOW_PATH = "./static/test.json"  # JSON파일 경로
 
app = Flask(__name__)
 
# ---------- 기능별 함수 ----------
def load_workflow(path: str) -> dict:
    """JSON 워크플로를 파일에서 읽기"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
 
def update_prompts(graph: dict, pos: str, neg: str,
                   pos_node_id: str = "6", neg_node_id: str = "7") -> dict:
    graph["13"]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
    graph[pos_node_id]["inputs"]["text"] = pos    
    graph[neg_node_id]["inputs"]["text"] = neg
    return graph
def submit_prompt(graph: dict) -> str:
    #ComfyUI /prompt 에 워크플로 제출 후 prompt_id 반환
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": graph})
    r.raise_for_status()
    return r.json()["prompt_id"]
 
def poll_history(prompt_id: str, timeout_sec: int = 60, interval: float = 1.0) -> dict | None:
    """
    간단 폴링: /history/{prompt_id} 에서 완료 결과를 받을 때까지 대기
    """
    end = time.time() + timeout_sec
    while time.time() < end:
        h = requests.get(f"{COMFY_URL}/history/{prompt_id}")
        if h.status_code == 200 and h.json():
            return list(h.json().values())[0]  # 해당 prompt의 히스토리 블록
        time.sleep(interval)
    return None
def extract_first_image_url(history_block: dict) -> str:
    """
    히스토리 블록에서 SaveImage 출력의 첫 번째 이미지를 view URL로 구성
    """
    if not history_block:
        return ""
    outputs = history_block.get("outputs", {})
    for node_id, node_out in outputs.items():
        if "images" in node_out and node_out["images"]:
            img = node_out["images"][0]
            fn  = img.get("filename")
            sub = img.get("subfolder", "")
            t   = img.get("type", "output")
            if fn:
                return f"{COMFY_URL}/view?filename={fn}&subfolder={sub}&type={t}"
    return ""
# ---------- Flask 라우트 ----------
@app.route("/", methods=["GET", "POST"])
def index():
    pos = request.form.get("pos", "a beautiful landscape with galaxy in a bottle")
    neg = request.form.get("neg", "text, watermark")
    img_url = ""
 
    if request.method == "POST":
        graph = load_workflow(WORKFLOW_PATH)
        graph = update_prompts(graph, pos, neg)  # 필요 시 노드 ID 인자 조정 가능
        prompt_id = submit_prompt(graph)
        history_block = poll_history(prompt_id)
        img_url = extract_first_image_url(history_block)
 
    return render_template("image.html", pos=pos, neg=neg, img_url=img_url)
 
if __name__ == "__main__":
    # pip install flask requests
    app.run(host="0.0.0.0", port=5000, debug=True)