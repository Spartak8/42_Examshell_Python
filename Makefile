.PHONY: help run practice real exam03 exam04

help:
	@echo "Available commands:"
	@echo "  make run       Start the interactive Exam Shell"
	@echo "  make practice  Choose an exam and start Practice mode"
	@echo "  make real      Choose an exam and start Real Exam mode"
	@echo "  make exam03    Open Exam 03 and choose a mode"
	@echo "  make exam04    Open Exam 04 and choose a mode"

run:
	python3 examshell.py

practice:
	python3 examshell.py --practice

real:
	python3 examshell.py --real

exam03:
	python3 examshell.py --exam 3

exam04:
	python3 examshell.py --exam 4
