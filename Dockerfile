FROM alpine:latest
WORKDIR /app

COPY static/bootstrap.bundle.min.js ./static/bootstrap.bundle.min.js
COPY static/bootstrap.min.css ./static/bootstrap.min.css
COPY templates/index.html ./templates/index.html
COPY app.py ./


RUN apk update
RUN apk add python3
RUN apk add py3-pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

EXPOSE 5000

ENTRYPOINT ["flask" , "run" , "--host=0.0.0.0"]
