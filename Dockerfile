FROM python:3.7-slim

RUN pip install --upgrade pip setuptools

WORKDIR /pubsub

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY pubsub pubsub

EXPOSE 8765

CMD ["python", "pubsub/app.py"]