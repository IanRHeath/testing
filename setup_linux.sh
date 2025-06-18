#!/bin/bash

# ============================================================================
# Jira Agent Setup Script for Linux/macOS
# ============================================================================
# This script will configure the necessary Python environment, install
# dependencies, and prompt for the required credentials to create the .env file.
# ============================================================================

echo ""
echo "=== Jira Agent Setup ==="
echo ""

# --- Step 1: Check for Python ---
echo "[1/5] Checking for Python 3 installation..."
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] python3 could not be found."
    echo "Please install Python 3.10 or higher."
    exit 1
fi
echo "      ...Python 3 found."
echo ""

# --- Step 2: Create a Python Virtual Environment ---
echo "[2/5] Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "      ...Virtual environment 'venv' already exists. Skipping creation."
else
    echo "      ...Creating virtual environment 'venv'. This may take a moment."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create the virtual environment."
        exit 1
    fi
    echo "      ...Virtual environment created successfully."
fi
echo ""

# --- Step 3: Install Dependencies ---
echo "[3/5] Installing required Python packages..."
source venv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install packages from requirements.txt."
    echo "Please check the file and your internet connection."
    exit 1
fi
deactivate
echo "      ...All packages installed successfully."
echo ""

# --- Step 4: Create the .env credentials file ---
echo "[4/5] Configuring credentials..."
if [ -f ".env" ]; then
    echo "      ...Existing .env file found. Skipping creation."
    echo "      (To re-create, please delete the .env file and run this script again)"
else
    echo "      ...Creating new .env file. Please enter your credentials below."
    echo ""
    
    read -p "Enter your JIRA Username: " JIRA_USER
    read -sp "Enter your JIRA Password/API Token: " JIRA_PASS
    echo "" # Newline after password input
    read -p "Enter your Azure OpenAI API Key: " LLM_KEY
    
    # Create the .env file with a combination of user input and hardcoded values
    cat > .env << EOF
JIRA_SERVER_URL=https://ontrack-internal.amd.com
JIRA_USERNAME=${JIRA_USER}
JIRA_PASSWORD=${JIRA_PASS}
LLM_API_KEY=${LLM_KEY}
LLM_API_VERSION=2024-06-01
LLM_RESOURCE_ENDPOINT=https://llm-api.amd.com
LLM_CHAT_DEPLOYMENT_NAME=gpt-4.1
EOF
    
    echo ""
    echo "      ...Successfully created .env file."
fi
echo ""

# --- Step 5: Create a Launcher Script ---
echo "[5/5] Creating launcher script..."
cat > run_app.sh << EOF
#!/bin/bash
echo "Activating virtual environment and starting Jira Agent backend..."
source venv/bin/activate
python app.py
EOF

# Make the launcher script executable
chmod +x run_app.sh
echo "      ...Created 'run_app.sh' for easy startup."
echo ""

# --- Done ---
echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To start the agent's backend server, run the following command:"
echo "./run_app.sh"
echo ""
echo "Then, start the frontend server to view the GUI."
echo ""
