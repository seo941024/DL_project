# 화면 서버 이미지: Prompt Studio 화면, ComfyUI 워크플로 제출. 이미지 생성은 COMFY_URL의 GPU 서버
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
COPY static/ static/
EXPOSE 5000
CMD ["python", "app.py"]
