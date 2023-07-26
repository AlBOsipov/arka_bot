FROM python:3.8

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip3 install -r ./requirements.txt --no-cache-dir
# RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "arka_bot.py"]
