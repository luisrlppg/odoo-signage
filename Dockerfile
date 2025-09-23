# Usamos Python 3.11 slim como base
FROM python:3.11-slim

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./app .

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "app.py"]