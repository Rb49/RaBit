from src.app import Application


def main():
    # run application
    Application()


if __name__ == '__main__':
    import tracemalloc
    tracemalloc.start()

    import sys
    if sys.version_info[0] != 3 or sys.version_info[1] < 10:
        raise Exception("Wrong Python version! Use version 3.10 and above.")

    main()
    sys.exit()
