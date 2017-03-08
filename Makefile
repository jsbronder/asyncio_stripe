PACKAGE = asyncio_stripe

SHELL = /bin/bash
TOPDIR := $(shell readlink -f $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON_VERSION ?= 3.5
VIRTUALENV ?= /usr/bin/env virtualenv

ACTIVATE = source .virtualenv$(PYTHON_VERSION)/bin/activate
TESTS = $(wildcard test/test_*.py)
VERSION = $(shell python setup.py --version)
MODULE_FILES = $(wildcard $(PACKAGE)/*.py)

.PHONY: test dist venv

all: virtualenv$(PYTHON_VERSION)

dist: dist/$(PACKAGE)-$(VERSION).tar.gz

venv: .virtualenv$(PYTHON_VERSION)/setup

.virtualenv$(PYTHON_VERSION)/setup: requirements.txt requirements-test.txt
	@$(VIRTUALENV) --python=python$(PYTHON_VERSION) .virtualenv$(PYTHON_VERSION)
	$(ACTIVATE); pip install \
			-r requirements.txt \
			-r requirements-test.txt
	touch .virtualenv$(PYTHON_VERSION)/setup

flake: venv
	@$(ACTIVATE); flake8 asyncio_stripe

build:
	$(ACTIVATE); python setup.py build


test: flake
	@failed=""; \
	for test in $(TESTS); do \
		echo "Testing $${test#*_}"; \
		$(ACTIVATE); python $${test} --verbose; \
		if [ $$? -ne 0 ]; then \
			failed+=" $${test}"; \
		fi; \
		echo;echo; \
	done; \
	if [ -n "$${failed}" ]; then \
		echo "Failed tests: $${failed}"; \
		exit 1; \
	else \
		echo "All tests passed."; \
	fi

dist/$(PACKAGE)-$(VERSION).tar.gz: venv $(MODULE_FILES) setup.py
	$(ACTIVATE); python setup.py sdist

dev-install: dist/$(PACKAGE)-$(VERSION).tar.gz
	$(ACTIVATE); pip install --no-deps \
		--upgrade --force-reinstall --no-index dist/$(PACKAGE)-$(VERSION).tar.gz

clean:
	rm -rf virtualenv[23]*
	rm -rf build
	rm -rf dist
	rm -rf $(PACKAGE).egg-info
