# EXP-0004: Inventory Vulkan protected-resource capabilities

## Question

What protected memory, queue, WSI, and video capabilities does the exact NVIDIA Linux stack advertise?

## Acceptance criterion

Every queried capability is reported as true, false, unsupported, or not tested; no GPU-model inference.

## Safety

Read-only runtime capability query on native Linux.
