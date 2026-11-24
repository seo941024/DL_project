"""연산 서버: KNN 모델로 품종 예측, GPU PC 로컬에서 실행. 8890 포트 /predict"""
import pickle

import numpy as np
from flask import Flask, jsonify, request

app = Flask(__name__)
with open('model/iris_model.pkl', 'rb') as f:
    model = pickle.load(f)
iris_names = ['setosa', 'versicolor', 'virginica']
iris_images = ['setosa.jpg', 'versicolor.jpg', 'Iris_virginica_2.jpg']
keys = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True)
    try:
        features = np.array([[float(data[k]) for k in keys]])
    except (KeyError, TypeError, ValueError) as e:
        return jsonify(error=f'입력 오류: {e}'), 400
    pred = int(model.predict(features)[0])
    return jsonify(prediction=iris_names[pred], image=iris_images[pred])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8890)
