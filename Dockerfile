# Use an official lightweight Python image
FROM python:3.9-slim
# Set the working directory inside the container
WORKDIR /app
COPY requirements.txt .
# Install only necessary packages
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install --yes --no-install-recommends build-essential ffmpeg wget pocketsphinx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# Copy only what's needed
COPY paved.py .
# Run the application
CMD ["python", "./paved.py"]
