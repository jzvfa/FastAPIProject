# 使用镜像加速拉取基础镜像（国内直连 docker.io 很慢）
# 若此镜像源失效，可改回：FROM python:3.11-slim，并在 /etc/docker/daemon.json 配 registry-mirrors
FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# pip 用清华源，加快安装依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
