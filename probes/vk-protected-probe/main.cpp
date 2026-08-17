#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstring>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string escape_json(const char* value) {
    std::ostringstream out;
    for (const unsigned char c : std::string(value ? value : "")) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) {
                    constexpr char hex[] = "0123456789abcdef";
                    out << "\\u00" << hex[(c >> 4) & 0xf] << hex[c & 0xf];
                } else {
                    out << static_cast<char>(c);
                }
        }
    }
    return out.str();
}

bool has_extension(const std::set<std::string>& extensions, const char* name) {
    return extensions.find(name) != extensions.end();
}

void print_schema() {
    std::cout << R"({
  "schema_version": 1,
  "description": "Fields emitted by vk-protected-probe",
  "states": ["CAPABILITY_ADVERTISED", "NOT_ADVERTISED", "NOT_TESTED", "ERROR"]
})" << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "--schema") == 0) {
        print_schema();
        return 0;
    }

    VkApplicationInfo app_info{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app_info.pApplicationName = "vk-protected-probe";
    app_info.applicationVersion = VK_MAKE_API_VERSION(0, 1, 0, 0);
    app_info.pEngineName = "none";
    app_info.apiVersion = VK_API_VERSION_1_1;

    VkInstanceCreateInfo create_info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    create_info.pApplicationInfo = &app_info;

    VkInstance instance = VK_NULL_HANDLE;
    const VkResult create_result = vkCreateInstance(&create_info, nullptr, &instance);
    if (create_result != VK_SUCCESS) {
        std::cerr << "vkCreateInstance failed: " << create_result << '\n';
        return 2;
    }

    std::uint32_t device_count = 0;
    VkResult result = vkEnumeratePhysicalDevices(instance, &device_count, nullptr);
    if (result != VK_SUCCESS) {
        std::cerr << "vkEnumeratePhysicalDevices failed: " << result << '\n';
        vkDestroyInstance(instance, nullptr);
        return 3;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    result = vkEnumeratePhysicalDevices(instance, &device_count, devices.data());
    if (result != VK_SUCCESS) {
        std::cerr << "vkEnumeratePhysicalDevices(list) failed: " << result << '\n';
        vkDestroyInstance(instance, nullptr);
        return 4;
    }

    std::cout << "{\n  \"schema_version\": 1,\n  \"physical_devices\": [\n";
    for (std::size_t device_index = 0; device_index < devices.size(); ++device_index) {
        VkPhysicalDevice physical = devices[device_index];
        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(physical, &properties);

        VkPhysicalDeviceProtectedMemoryFeatures protected_features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROTECTED_MEMORY_FEATURES};
        VkPhysicalDeviceFeatures2 features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};
        features.pNext = &protected_features;
        vkGetPhysicalDeviceFeatures2(physical, &features);

        std::uint32_t queue_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &queue_count, nullptr);
        std::vector<VkQueueFamilyProperties> queues(queue_count);
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &queue_count, queues.data());
        std::vector<std::uint32_t> protected_queues;
        for (std::uint32_t i = 0; i < queue_count; ++i) {
            if ((queues[i].queueFlags & VK_QUEUE_PROTECTED_BIT) != 0) protected_queues.push_back(i);
        }

        VkPhysicalDeviceMemoryProperties memory{};
        vkGetPhysicalDeviceMemoryProperties(physical, &memory);
        std::vector<std::uint32_t> protected_memory_types;
        for (std::uint32_t i = 0; i < memory.memoryTypeCount; ++i) {
            if ((memory.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_PROTECTED_BIT) != 0) protected_memory_types.push_back(i);
        }

        std::uint32_t extension_count = 0;
        vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, nullptr);
        std::vector<VkExtensionProperties> extension_properties(extension_count);
        vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, extension_properties.data());
        std::set<std::string> extensions;
        for (const auto& extension : extension_properties) extensions.emplace(extension.extensionName);

        if (device_index != 0) std::cout << ",\n";
        std::cout << "    {\n";
        std::cout << "      \"name\": \"" << escape_json(properties.deviceName) << "\",\n";
        std::cout << "      \"vendor_id\": " << properties.vendorID << ",\n";
        std::cout << "      \"device_id\": " << properties.deviceID << ",\n";
        std::cout << "      \"api_version\": " << properties.apiVersion << ",\n";
        std::cout << "      \"protected_memory_feature\": " << (protected_features.protectedMemory ? "true" : "false") << ",\n";
        std::cout << "      \"protected_queue_families\": [";
        for (std::size_t i = 0; i < protected_queues.size(); ++i) { if (i) std::cout << ", "; std::cout << protected_queues[i]; }
        std::cout << "],\n";
        std::cout << "      \"protected_memory_types\": [";
        for (std::size_t i = 0; i < protected_memory_types.size(); ++i) { if (i) std::cout << ", "; std::cout << protected_memory_types[i]; }
        std::cout << "],\n";
#ifdef VK_KHR_VIDEO_QUEUE_EXTENSION_NAME
        std::cout << "      \"video_queue_extension\": " << (has_extension(extensions, VK_KHR_VIDEO_QUEUE_EXTENSION_NAME) ? "true" : "false") << ",\n";
#else
        std::cout << "      \"video_queue_extension\": null,\n";
#endif
#ifdef VK_KHR_VIDEO_DECODE_QUEUE_EXTENSION_NAME
        std::cout << "      \"video_decode_queue_extension\": " << (has_extension(extensions, VK_KHR_VIDEO_DECODE_QUEUE_EXTENSION_NAME) ? "true" : "false") << ",\n";
#else
        std::cout << "      \"video_decode_queue_extension\": null,\n";
#endif
#ifdef VK_KHR_VIDEO_DECODE_H264_EXTENSION_NAME
        std::cout << "      \"video_decode_h264_extension\": " << (has_extension(extensions, VK_KHR_VIDEO_DECODE_H264_EXTENSION_NAME) ? "true" : "false") << ",\n";
#else
        std::cout << "      \"video_decode_h264_extension\": null,\n";
#endif
#ifdef VK_KHR_VIDEO_DECODE_H265_EXTENSION_NAME
        std::cout << "      \"video_decode_h265_extension\": " << (has_extension(extensions, VK_KHR_VIDEO_DECODE_H265_EXTENSION_NAME) ? "true" : "false") << ",\n";
#else
        std::cout << "      \"video_decode_h265_extension\": null,\n";
#endif
        std::cout << "      \"protected_surface\": {\"state\": \"NOT_TESTED\", \"reason\": \"no WSI surface supplied\"},\n";
        std::cout << "      \"protected_swapchain\": {\"state\": \"NOT_TESTED\", \"reason\": \"no WSI surface supplied\"},\n";
        std::cout << "      \"protected_video_profiles\": {\"state\": \"NOT_TESTED\", \"reason\": \"profile-specific query is the next probe revision\"}\n";
        std::cout << "    }";
    }

    std::cout << "\n  ]\n}\n";
    vkDestroyInstance(instance, nullptr);
    return 0;
}
