#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobs11.txt" done.txt; do python3 -c "import time; time.sleep(5)"; done
./runjobs.sh jobs12.txt 2 > jobs12.out 2>&1
