#!/bin/bash
# Script to build GridFlux from within MSYS2 environment
set -e

export PATH="/mingw64/bin:$PATH"

cd /c/Users/Admin/Documents/GitHub/GUI

echo "=== Testing gcc ==="
echo 'int main(){return 0;}' > /tmp/test.c
gcc /tmp/test.c -o /tmp/test.exe
echo "GCC OK"

echo "=== Cleaning build ==="
rm -rf build
mkdir build

echo "=== CMake Configure ==="
cmake -S . -B build -G "Ninja" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SERVER=ON \
  -DBUILD_CLI=ON

echo "=== Building ==="
cd build
ninja

echo "=== Build Complete ==="
ls -la bin/ lib/ 2>/dev/null || true