# Vulkan protected-resource capability probe

The probe reports only runtime-advertised Vulkan facts. It currently covers:

- `VkPhysicalDeviceProtectedMemoryFeatures::protectedMemory`;
- queue families with `VK_QUEUE_PROTECTED_BIT`;
- memory types with `VK_MEMORY_PROPERTY_PROTECTED_BIT`;
- presence of Vulkan Video device extensions.

Protected WSI and profile-specific protected-video capability/session queries are explicitly reported `NOT_TESTED` rather than inferred. They require a real surface and codec-profile-specific structures.

```bash
cmake -S . -B build -G Ninja
cmake --build build
./build/vk-protected-probe > vk-protected.json
```

Run on native Linux. WSL/WSLg results are not accepted as evidence for physical KMS or protected presentation.
