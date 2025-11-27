#! /bin/bash

# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
# SPDX-License-Identifier: Apache-2.0

# We run this wrapped in a script so it does not exit on error and we can time it out
# $1: <voltage in mV>.<frequency in MHz>

ROOT=$(dirname $(realpath $0))
WORKDIR=${ROOT}/runs/${1}

DUTCTL=/home/newt/dev/chimera/dutctl

voltage=$(echo $1 | cut -d. -f1)
frequency=$(echo $1 | cut -d. -f2)

echo "> Start measurement at ${voltage}mV and ${frequency}MHz"
cd $ROOT/.. && sed -e "s/__V__/${voltage}/" -e "s/__F__/${frequency}/" ${ROOT}/meas.gdb.in > ${WORKDIR}/script.gdb
cd $ROOT/.. && timeout -k 22 20 time -p ${DUTCTL} run -o0 common/chimera.openocd.hs2.tcl -t1 -g0 ${WORKDIR}/script.gdb --uart0 /dev/ttyUSB0:9600 -l ${WORKDIR}

echo "> Measurement finished, powering off DUT"
# Shut down in any case
cd $ROOT/.. && ${DUTCTL} poweroff