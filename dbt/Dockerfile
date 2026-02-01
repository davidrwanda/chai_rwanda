FROM python:3.11-slim

WORKDIR /dbt

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dbt (using compatible versions)
RUN pip install --no-cache-dir \
    dbt-core==1.8.0 \
    dbt-postgres==1.8.0 \
    protobuf==4.25.3

# Copy dbt project
COPY . .

CMD ["bash"]
