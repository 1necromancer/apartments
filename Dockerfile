FROM python:3.10-slim
RUN apt-get update && apt-get install -y libpq-dev gcc
WORKDIR /apartments-app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN mkdir -p /apartments-app/doc_result
COPY . .
EXPOSE 5000
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]