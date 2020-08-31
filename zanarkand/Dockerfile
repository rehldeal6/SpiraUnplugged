FROM python@sha256:f8ada9f1093eb4d5301a874cffd3e800761047cbdaae1772f3aaf79abf4082e3

WORKDIR /zanarkand

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY zanarkand.py /zanarkand/

ENTRYPOINT ["/zanarkand/zanarkand.py"]
