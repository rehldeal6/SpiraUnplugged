FROM python@sha256:f8ada9f1093eb4d5301a874cffd3e800761047cbdaae1772f3aaf79abf4082e3

RUN apk update && \
    apk add --no-cache ffmpeg git gcc libc-dev linux-headers && \
    pip3 install --no-cache-dir git+https://github.com/rehldeal6/SpiraUnplugged.git && \
    mkdir -p /opt/zanarkand/ && \
    apk del git

ADD agency-fb-bold.ttf /usr/share/fonts/agency-fb-bold/

ENTRYPOINT ["zanarkand.py"]
