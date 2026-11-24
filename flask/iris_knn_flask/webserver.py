"""화면 서버: 모델 없이 입력을 받아 연산 서버로 전달, VM에서 실행. 5000 포트
PREDICT_URL 기본값은 GPU PC 연산 서버"""
import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for

PREDICT_URL = os.environ.get('PREDICT_URL', 'http://192.168.24.106:8890/predict')
app = Flask(__name__)
app.secret_key = 'iris-knn-flask'
keys = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            r = requests.post(PREDICT_URL, json={k: request.form[k] for k in keys}, timeout=10)
            data = r.json()
            session['prediction'] = data.get('prediction') or data.get('error')
            session['image'] = data.get('image')
        except requests.RequestException as e:
            session['prediction'] = f'연산 서버 연결 오류: {e}'
            session['image'] = None
        return redirect(url_for('index'))
    return render_template('index.html', prediction=session.pop('prediction', None), image=session.pop('image', None))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
