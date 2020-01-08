FROM python:3.7-stretch

RUN apt-get update && apt-get install -y --no-install-recommends \
        vim \
    && rm -rf /var/lib/apt/lists/*

COPY . /deployment

WORKDIR /deployment

RUN pip install pip setuptools -U
RUN pip install -r requirements.txt

CMD ["bash"]
