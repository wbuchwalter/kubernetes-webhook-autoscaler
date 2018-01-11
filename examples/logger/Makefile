TARGETS= darwin/amd64 linux/amd64 windows/amd64
WHOAMI=$(shell whoami)
PROJECTNAME=logger

.PHONY: build

build:
	docker build \
	--file=./Dockerfile \
	--tag=$(WHOAMI)/$(PROJECTNAME):dev ./

debug:
	docker run --rm --name $(PROJECTNAME) \
	-it -p 5000:5000 \
	-v $(PWD):/app \
	$(WHOAMI)/$(PROJECTNAME):dev \
	/bin/bash

run:
	docker run --rm \
	-it -p 5000:5000 \
	-v $(PWD):/app \
	$(WHOAMI)/$(PROJECTNAME):dev \
	flask run --host=0.0.0.0

build-debug: build debug
build-run: build debug