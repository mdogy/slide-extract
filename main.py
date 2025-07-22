#!/usr/bin/env python3
"""
Command line script template
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description='Command line script')
    parser.add_argument('--version', action='version', version='1.0.0')
    
    args = parser.parse_args()
    
    print("Hello from your command line script!")


if __name__ == '__main__':
    main()