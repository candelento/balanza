import sys

REQUIRED = (3, 11)

def check():
    v = sys.version_info
    print(f"Python detected: {v.major}.{v.minor}.{v.micro}")
    if v < REQUIRED:
        print(f"Warning: Python {REQUIRED[0]}.{REQUIRED[1]}+ is recommended.")
    else:
        print("Python version OK.")

if __name__ == '__main__':
    check()
