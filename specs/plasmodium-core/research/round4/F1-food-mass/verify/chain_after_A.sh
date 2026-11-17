#!/bin/bash
cd "$(dirname "$0")"
while ! grep -q "DONE jobsA.txt" done.txt 2>/dev/null; do python3 -c "import time; time.sleep(3)"; done
python3 sched.py 3 > sched.out 2>&1
