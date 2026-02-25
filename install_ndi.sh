#!/bin/bash

cd /tmp
wget -q https://downloads.ndi.tv/SDK/NDI_SDK_Linux/Install_NDI_SDK_v5_Linux.tar.gz
tar -xzf Install_NDI_SDK_v5_Linux.tar.gz 2>/dev/null || true
echo "y" | sh Install_NDI_SDK_v5_Linux.sh

# Debug: show what's in /tmp after install
echo "Contents of /tmp:"
ls -la /tmp/

# The SDK might install to /tmp or current directory
# Search for it
echo "Searching for NDI SDK..."
find /tmp -maxdepth 2 -type d -name "NDI*" 2>/dev/null
find / -maxdepth 3 -type d -name "NDI*" 2>/dev/null

# Try multiple possible locations
for DIR in "/tmp/NDI SDK for Linux" "/NDI SDK for Linux" "./NDI SDK for Linux"; do
    if [ -d "$DIR" ]; then
        NDI_DIR="$DIR"
        break
    fi
done

# Also check for directory without "for"
if [ -z "$NDI_DIR" ]; then
    for DIR in "/tmp/NDI SDK" "/NDI SDK"; do
        if [ -d "$DIR" ]; then
            NDI_DIR="$DIR"
            break
        fi
    done
fi

if [ -z "$NDI_DIR" ]; then
    echo "ERROR: Could not find NDI SDK directory"
    echo "Listing all directories in /tmp:"
    ls -la /tmp/
    exit 1
fi

echo "Found NDI SDK at: $NDI_DIR"
echo "Contents:"
ls -la "$NDI_DIR"

# Copy includes
mkdir -p /usr/local/include/NDI
if [ -d "$NDI_DIR/include" ]; then
    cp -r "$NDI_DIR/include/"* /usr/local/include/NDI/
fi

# Copy library for x86_64
if [ -f "$NDI_DIR/lib/x86_64-linux-gnu/libndi.so.5.6.1" ]; then
    cp "$NDI_DIR/lib/x86_64-linux-gnu/libndi.so.5.6.1" /usr/local/lib/
elif [ -f "$NDI_DIR/lib/x86_64-linux-gnu/libndi.so" ]; then
    cp "$NDI_DIR/lib/x86_64-linux-gnu/libndi.so"* /usr/local/lib/
else
    echo "Looking for library files..."
    find "$NDI_DIR" -name "libndi*" 2>/dev/null
    # Try to copy whatever we find
    find "$NDI_DIR" -name "libndi.so*" -exec cp {} /usr/local/lib/ \;
fi

# Copy ndi-record binary
if [ -f "$NDI_DIR/bin/x86_64-linux-gnu/ndi-record" ]; then
    cp "$NDI_DIR/bin/x86_64-linux-gnu/ndi-record" /usr/local/bin/
    chmod +x /usr/local/bin/ndi-record
fi

# Create symlinks
cd /usr/local/lib
if [ -f libndi.so.5.6.1 ]; then
    ln -sf libndi.so.5.6.1 libndi.so.5
    ln -sf libndi.so.5 libndi.so
fi

ldconfig

echo "Installation complete!"
echo "Library files:"
ls -la /usr/local/lib/libndi* 2>/dev/null || echo "No library files found"
echo "Binary files:"
ls -la /usr/local/bin/ndi* 2>/dev/null || echo "No binary files found"