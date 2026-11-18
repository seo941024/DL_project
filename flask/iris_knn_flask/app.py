from flask import Flask, render_template, request, redirect, url_for, session  # 추가: redirect, url_for, session
import pickle
import numpy as np

# Flask 앱 생성
app = Flask(__name__)
app.secret_key = 'iris-knn-flask'  # 추가: session을 쓰려면 필요한 열쇠
# 저장된 모델 불러오기
with open('model/iris_model.pkl', 'rb') as f:
    model = pickle.load(f)
# 붓꽃 품종 이름과 static 폴더의 그림 파일. 같은 순서로 짝을 맞춘다
iris_names = ['setosa', 'versicolor', 'virginica']
iris_images = ['setosa.jpg', 'versicolor.jpg', 'Iris_virginica_2.jpg']


@app.route('/', methods=['GET', 'POST'])
def index():
    prediction = None
    image = None
    if request.method == 'POST':
        try:
            # 폼에서 값 가져오기
            sepal_length = float(request.form['sepal_length'])
            sepal_width = float(request.form['sepal_width'])
            petal_length = float(request.form['petal_length'])
            petal_width = float(request.form['petal_width'])
            # 입력 배열 생성
            features = np.array([[sepal_length, sepal_width, petal_length, petal_width]])
            # 예측
            pred = int(model.predict(features)[0])
            prediction = iris_names[pred]
            image = iris_images[pred]
        except Exception as e:
            prediction = f"입력 오류: {e}"
        session['prediction'] = prediction  # 추가: 결과를 잠깐 담아 두고
        session['image'] = image            # 추가
        return redirect(url_for('index'))   # 추가: 일반 주소로 다시 보낸다
    prediction = session.pop('prediction', None)  # 추가: 담아 둔 결과를 한 번만 꺼내 쓴다
    image = session.pop('image', None)            # 추가
    return render_template('index.html', prediction=prediction, image=image)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)