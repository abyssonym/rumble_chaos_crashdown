FROM python:2.7.9

RUN git clone --recursive https://github.com/abyssonym/rumble_chaos_crashdown.git
COPY entrypoint.sh /rumble_chaos_crashdown/entrypoint.sh
WORKDIR /rumble_chaos_crashdown
RUN chmod +x entrypoint.sh

VOLUME ["/input" "/output"]

CMD ["/bin/sh", "entrypoint.sh"]
