FROM python:3.10-bookworm

WORKDIR /app
RUN pip install redis flask Flask-Session requests
COPY main.py .
COPY static/ ./static
CMD [ "python", "main.py" ]