# Docker 기초 실습

## 개요

- 공식 이미지로 웹 서버·DB·Python 개발 환경 컨테이너 실행
- 포트 연결로 PC에서 컨테이너 서비스 접속
- 폴더 연결로 PC의 파일을 컨테이너 안에서 사용
- 컨테이너마다 단독 실행, 서로 연결하지 않는 구성

## 컨테이너 구성

| 컨테이너 | 이미지 | 포트 PC:컨테이너 | 폴더 연결 | 용도 |
|---|---|---|---|---|
| `myweb` | `httpd:latest` | 1234:80 | `apache/` → `/usr/local/apache2/htdocs` | Apache 웹 서버, 정적 HTML 제공 |
| `mariadb` | `mariadb` | 3307:3306 | Docker 볼륨 → `/var/lib/mysql` | MariaDB 서버, 데이터는 볼륨에 보관 |
| `devpython` | `python:3.12-slim` | 3000:3000 | `python/` → `/workspace` | Python 개발 환경, 대화형 실행 |

## 파일

```text
docker_basics/
├─ README.md
├─ apache/
│  └─ index.html     Apache 동작 확인 페이지
└─ python/
   └─ test.py        컨테이너 Python 실행 확인
```

## 실행 방법

`docker_basics` 폴더에서 실행

### Apache 웹 서버

```bash
docker run -d --name myweb -p 1234:80 -v "$PWD/apache":/usr/local/apache2/htdocs httpd:latest
```

브라우저 접속: `http://localhost:1234/`

### MariaDB

```bash
docker run -d --name mariadb -p 3307:3306 -e MYSQL_ROOT_PASSWORD=<비밀번호> mariadb
docker exec -it mariadb mariadb -uroot -p
```

PC의 DB 도구에서는 `localhost:3307`로 접속

### Python 개발 환경

```bash
docker run -it --name devpython -p 3000:3000 -v "$PWD/python":/workspace python:3.12-slim
```

다른 터미널에서 실행 확인

```bash
docker exec devpython python /workspace/test.py
```
