FROM python:3.7-stretch

RUN apt-get update && apt-get install -y --no-install-recommends \
        vim \
    && rm -rf /var/lib/apt/lists/*

COPY . /deployment

WORKDIR /deployment

RUN pip install pip setuptools -U
RUN pip install -r requirements.txt

RUN cd kubernetes && \
        ansible-galaxy collection install -r requirements.yml && \
    cd ../single-server && \
        ansible-galaxy collection install -r requirements.yml && \
        ansible-galaxy role install -r requirements.yml

CMD ["bash"]
