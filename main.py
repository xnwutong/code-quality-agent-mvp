import sys
from scanner import CodeQualityAgent


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "./"
    agent = CodeQualityAgent()
    agent.run_scan(target)
    agent.print_report()


if __name__ == "__main__":
    main()