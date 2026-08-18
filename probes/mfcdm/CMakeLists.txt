cmake_minimum_required(VERSION 3.24)

project(mfcdm_probe VERSION 1.0.0 LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "mfcdm-probe requires the Microsoft Windows SDK")
endif()

add_executable(mfcdm-probe mfcdm-probe.cpp)

target_compile_features(mfcdm-probe PRIVATE cxx_std_20)
target_compile_definitions(
    mfcdm-probe
    PRIVATE
        UNICODE
        _UNICODE
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        WINVER=0x0A00
        _WIN32_WINNT=0x0A00
        NTDDI_VERSION=0x0A000008
)
target_link_libraries(mfcdm-probe PRIVATE mfplat mfuuid ole32)

if(MSVC)
    target_compile_options(
        mfcdm-probe
        PRIVATE
            /W4
            /WX
            /permissive-
            /EHsc
            /utf-8
            /sdl
            /guard:cf
    )
    target_link_options(mfcdm-probe PRIVATE /guard:cf /DYNAMICBASE /NXCOMPAT)
endif()

install(TARGETS mfcdm-probe RUNTIME DESTINATION .)
