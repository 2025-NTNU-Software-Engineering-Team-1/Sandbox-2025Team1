#!/bin/bash

# sandbox binary
rm -f sandbox
wget https://github.com/2025-NTNU-Software-Engineering-Team-1/C-Sandbox-2025Team1/releases/latest/download/sandbox
chmod +x sandbox
# sandbox_interactive binary
rm -f sandbox_interactive
wget https://github.com/2025-NTNU-Software-Engineering-Team-1/C-Sandbox-2025Team1/releases/latest/download/sandbox_interactive
chmod +x sandbox_interactive

# c_cpp / python3 / interactive
docker build -t noj-c-cpp -f c_cpp_dockerfile . --no-cache
docker build -t noj-py3 -f python3_dockerfile . --no-cache
docker build -t noj-interactive -f interactive_dockerfile . --no-cache
docker build -t noj-custom-checker-scorer -f custom_checker_scorer_dockerfile . --no-cache

# create submissions folder
mkdir submissions
echo -e "\033[31mReplace working_dir in .config/submission.json with '$(pwd)/submissions'.\033[0m"
