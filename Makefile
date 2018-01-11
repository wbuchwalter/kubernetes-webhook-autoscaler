TARGETS= darwin/amd64 linux/amd64 windows/amd64
WHOAMI=$(shell whoami)
PROJECTNAME=k8sautoscaler

.PHONY: build

build:
	docker build \
	--file=./Dockerfile \
	--tag=$(WHOAMI)/$(PROJECTNAME):dev ./

debug:
	docker run --rm --name $(PROJECTNAME) \
	-it \
	-v $(PWD):/app \
	-v $(HOME)/.kube/config:/root/.kube/config \
	$(WHOAMI)/$(PROJECTNAME):dev \
	/bin/bash

build-debug: build debug
build-run: build debug