CC=gcc
CFLAGS=-std=c11 -O2 -pipe
TARGET=a.out

all: $(TARGET)

$(TARGET): main.c
	$(CC) $(CFLAGS) main.c -o $(TARGET)

clean:
	rm -f $(TARGET)
