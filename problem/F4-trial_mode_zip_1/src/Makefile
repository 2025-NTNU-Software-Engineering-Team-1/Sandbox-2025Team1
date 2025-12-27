CXX = g++
CXXFLAGS = -std=c++17 -O2

all: a.out

a.out: main.cpp utils.cpp
	$(CXX) $(CXXFLAGS) -o a.out main.cpp utils.cpp

clean:
	rm -f a.out
