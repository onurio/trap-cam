# syntax=docker/dockerfile:1

FROM python:3.9


WORKDIR /app

COPY ./src /app/src
COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
RUN apt-get update
RUN apt-get install python3-opencv -y

COPY . .

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000