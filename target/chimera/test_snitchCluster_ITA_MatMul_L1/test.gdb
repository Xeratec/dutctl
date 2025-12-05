# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
# SPDX-License-Identifier: Apache-2.0

target extended-remote localhost:3333

monitor reset halt

# Load binary
load deps/chimera-sdk/build/bin/test_snitchCluster_ITAMatMul_L1

set {int}0x03000000=1
set {int}0x03000004=240000
set {int}0x03000008=800
set {int}0x0300000c=300

# Launch binary
continue

# Exit from GDB
exit
