# =============================================================================
# GridFlux — Tiling Window Manager for Windows
# CMake build configuration
# =============================================================================

cmake_minimum_required(VERSION 3.16)
project(GridFlux VERSION 0.1.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# ── Build options ─────────────────────────────────────────────
option(BUILD_SERVER "Build the WM server binary" ON)
option(BUILD_CLI    "Build the CLI client binary" ON)
option(DEBUG_BUILD  "Enable debug logging" OFF)

# ── Output directories ────────────────────────────────────────
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# ── Common compile options ────────────────────────────────────
if(MSVC)
    add_compile_options(/W4 /WX-)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
else()
    add_compile_options(-Wall -Wextra -pedantic)
endif()

if(DEBUG_BUILD)
    add_definitions(-DGF_LOG_LEVEL=0)
else()
    add_definitions(-DGF_LOG_LEVEL=2)
endif()

# ── Source files ──────────────────────────────────────────────

# Core library (static)
set(CORE_SOURCES
    src/core/types.h
    src/core/layout.h
    src/core/layout.c
    src/core/wm.h
    src/core/wm.c
    src/core/wm_internal.h
    src/core/events.h
    src/core/events.c
    src/core/resize.h
    src/core/resize.c
    src/core/debug.h
    src/core/debug.c
    src/config/config.h
    src/config/config.c
    src/config/rules.h
    src/config/rules.c
    src/utils/list.h
    src/utils/memory.h
    src/utils/logger.h
    src/utils/logger.c
    src/utils/file_utils.h
    src/utils/file_utils.c
    src/utils/math_utils.h
    src/platform/platform.h
    src/manager/manager.h
    src/manager/manager.c
)

# Windows platform implementation
set(WIN32_PLATFORM_SOURCES
    src/platform/windows/platform.c
    src/platform/windows/internal.h
)

# IPC library
set(IPC_SOURCES
    src/ipc/ipc.h
    src/ipc/ipc.c
    src/ipc/ipc_handlers.h
    src/ipc/ipc_handlers.c
)

# ── Static library ────────────────────────────────────────────
add_library(gridflux_core STATIC
    ${CORE_SOURCES}
    ${WIN32_PLATFORM_SOURCES}
    ${IPC_SOURCES}
)

target_include_directories(gridflux_core PUBLIC ${CMAKE_SOURCE_DIR}/src)

# Link Windows libraries
target_link_libraries(gridflux_core PRIVATE
    DwmApi
)

# ── Server executable ─────────────────────────────────────────
if(BUILD_SERVER)
    add_executable(gridflux-server
        src/server/main.c
    )
    target_link_libraries(gridflux-server PRIVATE gridflux_core)
    set_target_properties(gridflux-server PROPERTIES
        WIN32 TRUE  # GUI subsystem (no console window)
        OUTPUT_NAME "gridflux"
    )
    # Actually we want console for debugging initially
    if(MSVC)
        set_target_properties(gridflux-server PROPERTIES
            LINK_FLAGS "/SUBSYSTEM:CONSOLE"
        )
    else()
        target_link_options(gridflux-server PRIVATE -Wl,-subsystem,console)
    endif()
endif()

# ── CLI executable ────────────────────────────────────────────
if(BUILD_CLI)
    add_executable(gridflux-cli
        src/cli/main.c
    )
    target_link_libraries(gridflux-cli PRIVATE gridflux_core)
    set_target_properties(gridflux-cli PROPERTIES
        OUTPUT_NAME "gf"
    )
endif()

# ── Installation rules ────────────────────────────────────────
install(TARGETS gridflux-server gridflux-cli
    RUNTIME DESTINATION bin
)

# ── Print configuration summary ──────────────────────────────
message(STATUS "")
message(STATUS "GridFlux build configuration:")
message(STATUS "  Version:      ${PROJECT_VERSION}")
message(STATUS "  Build type:   ${CMAKE_BUILD_TYPE}")
message(STATUS "  Debug build:  ${DEBUG_BUILD}")
message(STATUS "  Build server: ${BUILD_SERVER}")
message(STATUS "  Build CLI:    ${BUILD_CLI}")
message(STATUS "")
