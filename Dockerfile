FROM python:3.11-slim

WORKDIR /app

# Copy your backend code into the container
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "price_watcher.py"]