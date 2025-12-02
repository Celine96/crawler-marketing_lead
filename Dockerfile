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
```

6. **Commit new file** 클릭

---

### 2️⃣ email_crawler_render.py 교체

**업데이트된 파일 다운로드** → **GitHub에 업로드**

1. [email_crawler_render.py 다운로드](computer:///mnt/user-data/outputs/email_crawler_render.py) ← 클릭!
2. GitHub에서 기존 `email_crawler_render.py` 삭제
3. **Add file** → **Upload files**
4. 다운로드한 파일 드래그 앤 드롭
5. **Commit changes** 클릭

---

## 📋 빠른 체크리스트

- [ ] 1. 기존 Dockerfile **삭제**
- [ ] 2. 새 Dockerfile **생성** (위 코드 복사)
- [ ] 3. 기존 email_crawler_render.py **삭제**
- [ ] 4. 새 email_crawler_render.py **업로드**
- [ ] 5. Render에서 **재배포**

---

## 🎯 Render 재배포

파일 업데이트 완료 후:

1. **Render 대시보드** 접속
2. **crawler-marketing_lead** 서비스 클릭
3. **Manual Deploy** 탭
4. **Deploy latest commit** 버튼 클릭
5. **Logs** 탭에서 진행 상황 확인

### ✅ 성공하면 이렇게 보입니다:
```
==> Building Docker image...
✅ chromium installed
✅ chromium-driver installed  
✅ Python packages installed
==> Build successful!
