# 1. 파이썬 베이스 이미지 지정 (가볍고 안정적인 slim 버전)
FROM python:3.11-slim

# 2. 컨테이너 내부 시간을 KST(한국 시간)로 설정
# (bot.py 내부에서 pytz를 쓰지만, 시스템 로그와 컨테이너 OS 시간도 한국 시간으로 통일)
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스코드 및 나머지 파일 복사
COPY . .

# 6. 봇 실행
CMD ["python", "bot.py"]