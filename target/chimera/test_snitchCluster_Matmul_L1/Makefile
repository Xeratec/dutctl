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

meas-all:
	for v in {720..880..10}; do \
		for f in {25..650..25}; do \
		    make meas-$$v.$$f; \
		done; \
	done

.PHONY: runs/summary.json
runs/summary.json:
	python3 $(DUTCTL_ROOT)/util/parse_runs.py $(RUN) golden.json > $(RUN)/summary.json

plot-shmoo: runs/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/shmoo.py --title-suffix "INT8 MatMul 32x48x64" -m energy_efficiency -o $(RUN)/shmoo_energy_efficiency.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/shmoo.py --title-suffix "INT8 MatMul 32x48x64" -m power -o $(RUN)/shmoo_power.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/shmoo.py --title-suffix "INT8 MatMul 32x48x64" -m ops_per_second -o $(RUN)/shmoo_ops_per_second.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/shmoo.py --title-suffix "INT8 MatMul 32x48x64" -m ops_per_cycle -o $(RUN)/shmoo_ops_per_cycle.png $(RUN)/summary.json

plot-xy: runs/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/xy.py --title-suffix "INT8 MatMul 32x48x64" -m energy_efficiency -o $(RUN)/xy_energy_efficiency.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/xy.py --title-suffix "INT8 MatMul 32x48x64" -m power -o $(RUN)/xy_power.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/xy.py --title-suffix "INT8 MatMul 32x48x64" -m ops_per_second -o $(RUN)/xy_ops_per_second.png $(RUN)/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/xy.py --title-suffix "INT8 MatMul 32x48x64" -m ops_per_cycle -o $(RUN)/xy_ops_per_cycle.png $(RUN)/summary.json

plot-fit: runs/summary.json
	python3 $(DUTCTL_ROOT)/target/chimera/common/plot/fit.py --title-suffix "INT8 MatMul 32x48x64" -m energy_efficiency -o $(RUN)/result.csv $(RUN)/summary.json

plot: plot-shmoo plot-xy plot-fit