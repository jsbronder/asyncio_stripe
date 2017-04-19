PACKAGE = asyncio_stripe

SHELL = /usr/bin/env bash
TOPDIR := $(shell readlink -f $(dir $(lastword $(MAKEFILE_LIST))))

TESTS = $(wildcard test/test_*.py)
VERSION = $(shell python setup.py --version)
MODULE_FILES = $(wildcard $(PACKAGE)/*.py)

.PHONY: test dist

all:

dist: dist/$(PACKAGE)-$(VERSION).tar.gz

requirements: requirements.txt requirements-test.txt
	@pip install -r requirements.txt -r requirements-test.txt

flake:
	@flake8 asyncio_stripe/

test: flake
	@failed=""; \
	for test in $(TESTS); do \
		echo "Testing $${test#*_}"; \
		python $${test} --verbose; \
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

dist/$(PACKAGE)-$(VERSION).tar.gz: $(MODULE_FILES) setup.py
	python setup.py sdist

install: dist
	pip install --no-deps \
		--upgrade --force-reinstall --no-index dist/$(PACKAGE)-$(VERSION).tar.gz

uninstall:
	pip uninstall --yes $(PACKAGE)

clean:
	rm -rf build
	rm -rf dist
	rm -rf $(PACKAGE).egg-info
