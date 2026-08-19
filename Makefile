.PHONY: install seed train dev test demo

install:
	python scripts/commands.py install
seed:
	python scripts/commands.py seed
train:
	python scripts/commands.py train
dev:
	python scripts/commands.py dev
test:
	python scripts/commands.py test
demo:
	python scripts/commands.py demo
