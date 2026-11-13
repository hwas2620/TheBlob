#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobs6.txt" done.txt; do python3 -c "import time; time.sleep(5)"; done
./runjobs.sh jobs7.txt 4 > jobs7.out 2>&1
