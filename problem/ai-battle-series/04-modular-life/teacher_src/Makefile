CC=gcc
CFLAGS=-std=c11 -O2 -pipe -static -s -lm

all: a.out

a.out: main.c function.h
	$(CC) $(CFLAGS) main.c -o a.out

clean:
	rm -f a.out
