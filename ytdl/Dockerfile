FROM python@sha256:af555a32c066d814736ce1068817749fbafdf0b88461f970c3df6f7bf110d1d2

WORKDIR /zanarkand

COPY requirements.txt .
COPY zanarkand_ytdl.sh .

RUN pip install -r requirements.txt && \
    chmod 0777 /zanarkand/zanarkand_ytdl.sh

ENTRYPOINT ["/zanarkand/zanarkand_ytdl.sh"]
