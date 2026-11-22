# 웹 서버 이미지: 채팅 화면, POST 처리, Ollama 호출
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
EXPOSE 5000
CMD ["python", "app.py"]
