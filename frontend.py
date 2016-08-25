#!/usr/local/env python
import argparse
from frontend.securitybot_frontend import main, init

if __name__ == '__main__':
    init()

    parser = argparse.ArgumentParser(description='Securitybot frontent')
    parser.add_argument('--port', dest='port', default='8888', type=int)
    args = parser.parse_args()

    main(args.port)
