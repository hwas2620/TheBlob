#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobs8.txt" done.txt; do python3 -c "import time; time.sleep(5)"; done
./runjobs.sh jobs9.txt 3 > jobs9.out 2>&1
