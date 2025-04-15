FROM python:3.12-alpine

WORKDIR /app
COPY . .

# RUN apk add --no-cache gcc musl-dev

# RUN apk add --no-cache python3-dev libffi-dev openssl-dev
# RUN python3.12 -m ensurepip --upgrade
# RUN python3.12 -m pip install --upgrade pip setuptools

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--port", "8080", "--host=0.0.0.0", "--log-config=log_conf.yaml"]
