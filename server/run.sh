#!/bin/bash

nohup poetry run python3 server.py --port 8082 >> log.txt 2>&1  &
