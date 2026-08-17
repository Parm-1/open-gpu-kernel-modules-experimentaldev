cmake_minimum_required(VERSION 3.20)
project(vk_protected_probe LANGUAGES CXX)

find_package(Vulkan REQUIRED)
add_executable(vk-protected-probe main.cpp)
target_link_libraries(vk-protected-probe PRIVATE Vulkan::Vulkan)
target_compile_features(vk-protected-probe PRIVATE cxx_std_17)
target_compile_options(vk-protected-probe PRIVATE -Wall -Wextra -Wpedantic)
