FROM python:2.7.9

RUN git clone --recursive https://github.com/abyssonym/rumble_chaos_crashdown.git
COPY docker-entrypoint.sh /rumble_chaos_crashdown/docker-entrypoint.sh
WORKDIR /rumble_chaos_crashdown
RUN chmod +x docker-entrypoint.sh

VOLUME ["/input" "/output"]

CMD ["/bin/sh", "docker-entrypoint.sh"]
