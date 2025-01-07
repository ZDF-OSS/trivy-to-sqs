.PHONY: start install source

init:
	source .env/bin/activate

install:
	pip install -r requirements.txt

start: install
	python main.py
