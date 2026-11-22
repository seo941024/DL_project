import pickle
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
# 1. 데이터 불러오기
iris = datasets.load_iris()
X = iris.data
y = iris.target
# 2. 학습/검증/테스트 7:2:1 분리
X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.1, stratify=y, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_rest, y_rest, test_size=2/9, stratify=y_rest, random_state=42)
print(len(X_train), len(X_val), len(X_test))
# 3. KNN 모델 생성 및 학습
knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(X_train, y_train)
# 4. 검증·테스트 정확도
print(f"검증 정확도: {knn.score(X_val, y_val):.1%}")
print(f"테스트 정확도: {knn.score(X_test, y_test):.1%}")
# 5. 모델 저장
import os
os.makedirs('model', exist_ok=True)
with open('model/iris_model.pkl', 'wb') as f:
    pickle.dump(knn, f)
print("모델이 model/iris_model.pkl로 저장되었습니다.")