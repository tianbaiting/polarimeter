cmake_minimum_required(VERSION 3.20)

project(dpolar_reco LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DPOLAR_BUILD_TESTS "Build dpolar regression tests" ON)

find_package(ROOT REQUIRED COMPONENTS Core Graf Gpad Hist Physics)

add_library(dpolar_core STATIC
    src/config.cpp
    src/kinematics.cpp
    src/observables.cpp
    src/acceptance.cpp
    src/counts.cpp
    src/inference.cpp
    src/inference_plot.cpp
    src/energy_loss.cpp
    src/plotting.cpp
    src/analysis.cpp
)

target_include_directories(dpolar_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_definitions(dpolar_core
    PUBLIC
        DPOLAR_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
)

target_link_libraries(dpolar_core
    PUBLIC
        ROOT::Core
        ROOT::Graf
        ROOT::Gpad
        ROOT::Hist
        ROOT::Physics
)

add_library(dpolar_capi SHARED src/c_api.cpp)
target_include_directories(dpolar_capi PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(dpolar_capi PUBLIC dpolar_core)
set_target_properties(dpolar_capi PROPERTIES OUTPUT_NAME dpolar_capi)

add_executable(dpol_tool apps/dpol_tool.cpp)
target_link_libraries(dpol_tool PRIVATE dpolar_core ROOT::Core)

add_executable(dpol_batch apps/dpol_batch.cpp)
target_link_libraries(dpol_batch PRIVATE dpolar_core ROOT::Core)

if(DPOLAR_BUILD_TESTS)
    enable_testing()
    add_executable(dpolar_tests tests/test_main.cpp)
    target_link_libraries(dpolar_tests PRIVATE dpolar_core ROOT::Core)
    add_test(NAME dpolar_tests COMMAND dpolar_tests)
endif()
