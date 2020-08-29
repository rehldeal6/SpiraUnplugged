#FROM python@sha256:f8ada9f1093eb4d5301a874cffd3e800761047cbdaae1772f3aaf79abf4082e3
FROM python@sha256:ee2da4ef36f8b0f3bf076450712ab797418fc68676fa7686490ab307a7ddbdcd

WORKDIR /zanarkand

COPY requirements.txt .

RUN apt update && \
    apt install -y ffmpeg && \
    pip install -r requirements.txt

ADD agency-fb-bold.ttf /usr/share/fonts/agency-fb-bold/
COPY zanarkand_ffmpeg.py .

ENTRYPOINT ["python", "/zanarkand/zanarkand_ffmpeg.py"]
