# 화면 서버 이미지: Flask 화면, LangChain 구조화 번역 요청, ComfyUI 이미지 요청
# 모델 계산은 하지 않음. OLLAMA_URL·COMFY_URL로 GPU PC의 Ollama·ComfyUI를 호출
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
COPY static/ static/
EXPOSE 5000
CMD ["python", "app.py"]
