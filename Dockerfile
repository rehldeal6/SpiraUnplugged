FROM python@sha256:f8ada9f1093eb4d5301a874cffd3e800761047cbdaae1772f3aaf79abf4082e3

RUN apk update && \
    apk add ffmpeg git gcc libc-dev linux-headers && \
    rm -rf /var/cache/apk/* && \
    pip3 install git+https://github.com/rehldeal6/SpiraUnplugged.git && \
    mkdir -p /opt/zanarkand/

ENTRYPOINT ["zanarkand.py"]
