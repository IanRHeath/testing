# Jira Triage LLM Agent

## Overview

The Jira Triage LLM Agent is a powerful, conversational AI tool designed to streamline interaction with a Jira instance. It leverages a Large Language Model (LLM) to understand natural language queries, allowing users to search for tickets, perform complex analysis, and create new issues through a user-friendly graphical interface.

This tool is built with a Python Flask backend that houses the core agent logic and a React-based frontend for the user interface.

## Features

This agent is equipped with a rich set of features designed to enhance productivity and improve Jira data quality.

#### 1. **Advanced Ticket Searching & Filtering**
* **Natural Language Queries:** Search for tickets using plain English (e.g., "find tickets about system hangs").
* **Time-Based Filtering:** Filter issues by creation or update date using relative terms like "last week," "past year," or "since yesterday."
* **User-Based Filtering:** Find tickets assigned to or reported by specific users, including the special keyword "me" (e.g., "show me tickets assigned to me").
* **Flexible Stale Ticket Detection:** Identify tickets that haven't been updated within a configurable time frame (e.g., "find tickets untouched for 90 days").
* **Combined Filters:** Layer multiple criteria together for highly specific searches (e.g., "show me 2 critical STXH tickets created in the last month").

#### 2. **In-Depth Ticket Analysis**
* **AI-Powered Summaries:** Generate detailed, structured summaries for single or multiple tickets, covering problem statements, root causes, and blockers.
* **Aggregate Analysis:** When summarizing multiple tickets, the agent provides a high-level "meta-summary" that identifies common themes and patterns across the entire set.
* **High-Accuracy Duplicate Detection:** Find potential duplicate tickets by combining precise field filtering (Project, Program) with an AI-driven semantic comparison of ticket summaries.

#### 3. **Conversational Ticket Creation**
* **Guided, Step-by-Step Flow:** The agent walks the user through the creation process one question at a time.
* **Interactive Options:** For fields with predefined choices (like Program or Severity), the GUI presents dropdowns or clickable buttons to prevent errors.
* **Proactive Duplicate Check:** Before a new ticket is finalized, the agent automatically searches for potential duplicates and warns the user, helping to keep Jira clean.

#### 4. **Modern User Interface**
* **Full GUI:** A polished, chat-based interface for all interactions.
* **Dark Mode:** A toggle for user comfort.
* **Persistent Theme:** Remembers your light/dark mode preference.
* **Helper Utilities:** Includes suggestion chips for common commands and a "copy to clipboard" button for ticket details.

## Getting Started
Follow these steps to set up and run the application on a new machine.


### **1. Backend Setup**

These steps configure the Python server that powers the agent.

1.  Navigate to the `/backend` directory in your terminal.
2.  If you are on **Windows**, double-click the `setup_windows.bat` script.
3.  If you are on **Linux or macOS**, run the following commands:
    ```bash
    chmod +x setup_linux.sh
    ./setup_linux.sh
    ```
4.  The setup script will prompt you to enter your Jira Username, Jira Password/Token, and your Azure LLM API Key. It will securely save these into a new `.env` file.

### **2. Frontend Setup**

These steps configure the graphical user interface.

1.  Navigate to the `/frontend` directory in your terminal.
2.  If you are on **Windows**, double-click the `setup_frontend.bat` script.
3.  If you are on **Linux or macOS**, run the following commands:
    ```bash
    chmod +x setup_frontend.sh
    ./setup_frontend.sh
    ```
4.  This script will check for Node.js, clean up any old files, and install all the necessary packages for the UI.

## How to Use

To run the application, you must start both the backend and frontend servers.

1.  **Start the Backend:**
    * **Windows:** Double-click `run_app.bat` inside the `/backend` folder.
    * **Linux/macOS:** From the `/backend` folder, run `./run_app.sh`.
    * A terminal window will appear, indicating the backend server is running. Leave this window open.

2.  **Start the Frontend:**
    * **Windows:** Double-click `run_frontend.bat` inside the `/frontend` folder.
    * **Linux/macOS:** From the `/frontend` folder, run `./run_frontend.sh`.
    * This will automatically open a new tab in your web browser with the chat GUI.

You can now interact with the agent through the GUI.

### **Example Prompts**

Here are a few examples of how to use the agent's features:

* `show me 3 critical plat tickets`
* `what tickets are assigned to me`
* `find issues reported by Ian Heath`
* `find tickets created in the last week`
* `find stale tickets not updated in 90 days`
* `summarize PLAT-12345`
* `summarize PLAT-12345 and PLAT-54321`
* `find duplicates for PLAT-179648`
* `create a new ticket`

