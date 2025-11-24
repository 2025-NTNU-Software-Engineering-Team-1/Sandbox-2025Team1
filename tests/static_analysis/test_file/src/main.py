# test_target.py
import sys


def sort(data):
    print("User defined global sort")


def func_a(n):
    if n > 0:
        func_b(n - 1)


def func_b(n):
    if n > 0:
        func_a(n - 1)


class MySorter:

    def __init__(self):
        self.data = []

    def sort(self):
        print("MySorter.sort called")

    def helper(self):
        print("Helper")

    def main_algo(self):
        self.helper()
        self.sort()

    def fake_sort(self, external_list):
        external_list.sort()


def main():
    raw_list = [3, 1, 2]

    raw_list.sort()

    sort(raw_list)

    s = MySorter()
    s.sort()

    s.main_algo()

    s.fake_sort(raw_list)

    func_a(5)


if __name__ == "__main__":
    main()
