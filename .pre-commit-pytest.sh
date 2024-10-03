#!/bin/bash

# Function to run pytest in directories
run_pytest() {
  # Loop through each directory
  for dir in $1; do
    # Check if the directory exists and starts with 'intentional'
    if [[ -d "$dir" && "$dir" == intentional* ]]; then
      # Navigate to the directory, run pytest, then return to the original directory
      echo "Running pytest in $dir"
      (cd "$dir" && pytest)
    fi
  done
}


echo "Running pytest in intentional-core/"
pytest intentional-core/
cd plugins

if [[ $1 == "all" ]]; then
  # If argument is 'all', find all directories starting with 'intentional'
  all_dirs=$(find . -type d -name 'intentional*' -printf '%f\n' | sort -u)
  run_pytest "$all_dirs"
else
  # Otherwise, get the list of changed directories starting with 'intentional'
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | awk -F'/' '{print $1}' | sort -u)
  run_pytest "$changed_dirs"
fi
