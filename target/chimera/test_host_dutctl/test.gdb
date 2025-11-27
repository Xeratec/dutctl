# Copyright 2025 ETH Zurich and University of Bologna.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Paul Scheffler <paulsc@iis.ee.ethz.ch>
# Thomas Benz <tbenz@iis.ee.ethz.ch>

target extended-remote localhost:3333

# Load binary
load deps/chimera-sdk/build/bin/test_host_dutctl

set {int}0x03000000=780
set {int}0x03000004=100

# Launch binary
continue

# Read scratch reg 2
x/d 0x03000000
x/d 0x03000004
x/d 0x03000008

# Exit from GDB
exit
