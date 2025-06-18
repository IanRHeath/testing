#!/bin/bash

# ============================================================================
# Jira Agent Frontend SETUP Script for Linux/macOS
# ============================================================================
# DESCRIPTION:
# This script should be run ONLY ONCE to set up the frontend environment
# or when you are experiencing issues with dependencies. It will:
# 1. Check for Node.js/npm.
# 2. Clean up any old installations.
# 3. Install all necessary packages.
# ============================================================================

echo ""
echo "=== Jira Agent Frontend Setup ==="
echo ""

# --- Step 1: Prerequisite Check ---
echo "[1/4] Checking for Node.js and NPM..."
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null
then
    echo "[ERROR] Node.js or NPM could not be found."
    echo "The recommended way to install Node.js is with NVM (Node Version Manager)."
    echo "Please visit https://github.com/nvm-sh/nvm for installation instructions."
    exit 1
fi
echo "      ...Node.js and NPM found."
echo ""

# --- Step 2: Clean Up Old Dependencies ---
echo "[2/4] Cleaning up previous installation..."
if [ -d "node_modules" ]; then
    echo "      ...Removing 'node_modules' directory. This may take a moment."
    rm -rf node_modules
fi
if [ -f "package-lock.json" ]; then
    echo "      ...Removing 'package-lock.json' file."
    rm package-lock.json
fi
echo "      ...Cleanup complete."
echo ""

# --- Step 3: Install Fresh Dependencies ---
echo "[3/4] Installing Node.js packages..."
npm install
if [ $? -ne 0 ]; then
    echo "[ERROR] 'npm install' failed. Please check your Node.js/npm installation and network connection."
    exit 1
fi
echo "      ...Dependencies installed successfully."
echo ""

# --- Step 4: Done ---
echo "[4/4] Setup Complete!"
echo ""
echo "You can now run the frontend application by executing './run_frontend.sh'."
echo ""
