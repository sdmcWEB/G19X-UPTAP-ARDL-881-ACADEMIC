FROM python:3.12-slim

# Tesseract (español) y utilidades que OCRmyPDF necesita
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa \
        ghostscript qpdf unpaper pngquant \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY pyproject.toml ./
# Caché de BuildKit: la imagen sigue sin llevar la caché dentro, pero un
# cambio en pyproject.toml ya no obliga a volver a bajar PyTorch (~2 GB).
RUN --mount=type=cache,target=/root/.cache/pip pip install -e ".[dev,ml]"
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
