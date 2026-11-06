PYTHON ?= python3
RUFF ?= ruff
export PYTHONPATH := $(CURDIR)

.PHONY: check test lint sources summary
check: lint test

test:
	$(PYTHON) -W error -m unittest discover -v

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	bash -n mkosi.postinst.chroot mkosi.finalize mkosi.initrd.conf/mkosi.postinst mkosi.initrd.conf/mkosi.extra/usr/libexec/particleve-initrd-storage

sources:
	$(PYTHON) tools/fetch-sources.py

summary:
	mkdir -p build
	build/sources/mkosi/bin/mkosi --json summary > build/summary.json
	$(PYTHON) tools/check-build.py --summary build/summary.json
