FROM alpine:3.17

WORKDIR /app

RUN apk add --no-cache gcc musl-dev

ENV WELCOME_MSG="Welcome to the Interactive API!"
ENV CHALLENGE_ANSWER="42"

COPY server.c .

RUN gcc -o server server.c

EXPOSE 9002

CMD ["./server"]
