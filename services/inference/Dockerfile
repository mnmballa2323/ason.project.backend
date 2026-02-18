# Base Image: Pinned for reproducibility
FROM vllm/vllm-openai:v0.3.3

# Set working directory
WORKDIR /app

# Install service dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

# Environment Variables for vLLM
ENV MODEL_PATH=/models/ason-72b-instruct
ENV PORT=8000

# Expose port
EXPOSE 8000

# Entrypoint: Run the FastAPI wrapper, not the raw vLLM server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
