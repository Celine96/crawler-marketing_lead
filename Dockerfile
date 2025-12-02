# Render용 이메일 크롤러 Dockerfile
# Chromium + Selenium 환경 (가장 간단하고 안정적)

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# Chromium 및 ChromeDriver 설치 (Debian 저장소에서)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Chromium 경로 환경 변수 설정
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 기본 명령어
CMD ["python", "email_crawler_render.py"]
