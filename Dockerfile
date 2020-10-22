FROM python:2.7.9

RUN git clone --recursive https://github.com/abyssonym/rumble_chaos_crashdown.git
COPY docker-entrypoint.sh /rumble_chaos_crashdown/docker-entrypoint.sh
WORKDIR /rumble_chaos_crashdown
RUN chmod +x docker-entrypoint.sh \
    && rm changelog.txt README README.日本語 fft_rcc.exe .gitignore .gitmodules \
    && rm -rf .git gallery

VOLUME ["/input" "/output"]

CMD ["/bin/sh", "docker-entrypoint.sh"]
