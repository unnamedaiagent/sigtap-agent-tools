FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S mcp && adduser -S mcp -G mcp
COPY mcp_server.py .
USER mcp
ENTRYPOINT ["python3", "mcp_server.py"]
