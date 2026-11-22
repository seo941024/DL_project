#pip install flask requests
# 웹 서버: 화면만 담당. 모델이 없어서 추론은 워크스테이션의 app.py에 요청
import os
import requests
from flask import Flask, request, jsonify, render_template
app = Flask(__name__)
GPU_URL = os.environ.get("GPU_URL", "http://host.docker.internal:8888/predict")

@app.route("/predict", methods=["POST"])
def predict():
    """
    multipart/form-data: file 필드로 이미지 업로드
    """
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    r = requests.post(GPU_URL, files={"file": (f.filename, f.stream, f.mimetype)})
    result = r.json()
    return jsonify(result)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
