FROM python:2.7.15-alpine3.7

RUN apk add --no-cache build-base postgresql-dev linux-headers pcre-dev \
                       libffi-dev

WORKDIR /usr/src/app

COPY requirements/ ./requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manager.py", "runserver"]
