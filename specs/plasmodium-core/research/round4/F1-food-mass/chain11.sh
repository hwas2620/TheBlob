#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobs10.txt" done.txt; do python3 -c "import time; time.sleep(5)"; done
./runjobs.sh jobs11.txt 3 > jobs11.out 2>&1
