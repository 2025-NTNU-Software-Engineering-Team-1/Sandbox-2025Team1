FROM alpine:3.17

WORKDIR /app

RUN apk add --no-cache g++

COPY server.cpp .

RUN g++ server.cpp -o server

CMD ["./server"]