FROM python:3.11-slim

# Install system dependencies and Google Chrome directly via deb package
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm ./google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data and ChromeDriver
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
RUN python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

COPY app.py .

EXPOSE 7000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7000"]
