# 1. Base Image
FROM python:3.10-slim AS base

# 2. Environment Variables & Working Directory
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_NO_INTERACTION=1

WORKDIR /app

# 3. Install System Dependencies (if any, none specified for now)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package

# 4. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Application Code
# Copy the source code for the application
COPY ./src ./src
# Copy .env.example for reference (optional, but can be good)
# It's important that the actual .env file is not copied into the image for security.
# It should be provided at runtime.
COPY .env.example .

# 6. Create a non-root user and group & set up permissions
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# The application will create the 'storage' directory if it doesn't exist.
# However, to ensure the appuser has permissions to create and write to it
# under /app, we ensure /app itself is owned by appuser.
# The config.py will then create /app/storage, and it will inherit ownership correctly.
# If storage dir were created by root here, appuser might not have write access.
# Alternative: create /app/storage here and chown it, as requested.
RUN mkdir /app/storage && chown appuser:appgroup /app/storage
# Ensure the rest of the app directory is also owned by appuser
RUN chown -R appuser:appgroup /app

# 7. Switch to non-root user
USER appuser

# 8. Expose Port
# The port should match the one Uvicorn will run on.
# Defaulting to 8000 as per common practice and settings.
EXPOSE 8000

# 9. Command to Run Application
# This command assumes that src.main:app is the FastAPI application instance
# and that settings.PORT is used by main.py if __name__ == "__main__" or by uvicorn directly.
# The Dockerfile's EXPOSE and CMD port should ideally match.
# If settings.PORT can vary, the CMD here should reflect that, e.g., by reading an ENV var.
# For now, hardcoding to 8000 as per instructions.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
