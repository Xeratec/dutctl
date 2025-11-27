# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
# SPDX-License-Identifier: Apache-2.0

SHELL := bash

DUTCTL_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || echo $$DUTCTL_ROOT)

RUN ?= runs/

# Extracting word nr. $(1) from $(2)-separated list $(3)
pw = $(word $(1), $(subst $(2), ,$(3)))

meas-%: meas.gdb.in run_dutctl.sh
	@echo "=== VOLTAGE: $(call pw,1,.,$*) mV, FREQ: $(call pw,2,.,$*) MHz ==="
	mkdir -p runs/$*
	./run_dutctl.sh $*
	@echo "======"
	@echo

meas:
	for v in {720..720..10}; do \
		for f in {25..650..25}; do \
		    make meas-$$v.$$f; \
		done; \
	done

.PHONY: runs/summary.json
runs/summary.json:
	python3 $(DUTCTL_ROOT)/util/parse_runs.py $(RUN) golden.json > $(RUN)/summary.json

plot-shmoo: runs/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/shmoo.py -m power -o shmoo_power.png $(RUN)/summary.json

plot-xy: runs/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/xy.py -m power -o xy_power.png $(RUN)/summary.json

plot: plot-shmoo plot-xy

all: meas plot