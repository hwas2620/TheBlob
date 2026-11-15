#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobs9.txt" done.txt; do python3 -c "import time; time.sleep(5)"; done
./runjobs.sh jobs10.txt 3 > jobs10.out 2>&1
