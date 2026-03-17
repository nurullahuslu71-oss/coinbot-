FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install requests
CMD ["python", "coinbot2.py"]
