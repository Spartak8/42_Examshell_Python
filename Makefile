.PHONY: help run practice real exam02 exam03 exam04

help:
	@echo Available commands:
	@echo   make run       Start the interactive Exam Shell
	@echo   make practice  Choose an exam and start Practice mode
	@echo   make real      Choose an exam and start Real Exam mode
	@echo   make exam02    Open Exam 02 (C) and choose a mode
	@echo   make exam03    Open Exam 03 and choose a mode
	@echo   make exam04    Open Exam 04 and choose a mode

run:
	python examshell.py

practice:
	python examshell.py --practice

real:
	python examshell.py --real

exam02:
	python examshell.py --exam 2

exam03:
	python examshell.py --exam 3

exam04:
	python examshell.py --exam 4
