FROM debian:10

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        psutils \
        python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -m 0700 /root/.ssh && mkdir -m 0755 /run/sshd

VOLUME ["/home/openzaak"]

COPY ./start_vm.sh /start_vm.sh

EXPOSE 22

CMD ["/start_vm.sh"]
