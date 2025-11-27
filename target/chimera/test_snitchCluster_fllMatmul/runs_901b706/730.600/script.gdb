# Copyright 2025 ETH Zurich and University of Bologna.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

target extended-remote localhost:3333

monitor reset halt

# Load binary
load deps/chimera-sdk/build/bin/test_snitchCluster_fllMatmul

set {int}0x03000000=1
set {int}0x03000004=24000
set {int}0x03000008=730
set {int}0x0300000C=600

# Launch binary
continue

# Exit from GDB
exit
