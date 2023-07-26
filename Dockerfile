FROM python:3.8

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip3 install -r ./requirements.txt --no-cache-dir


COPY . .

CMD ["python", "arka_bot.py"]
