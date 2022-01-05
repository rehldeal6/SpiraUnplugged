FROM python@sha256:a7deebfd654d0158999e9ae9a78ce4a9c7090816a2d1600d254fef8b7fd74cac

WORKDIR /zanarkand

COPY requirements.txt .
COPY zanarkand_ytdl.sh .

RUN pip install -r requirements.txt && \
    chmod 0777 /zanarkand/zanarkand_ytdl.sh

ENTRYPOINT ["/zanarkand/zanarkand_ytdl.sh"]
