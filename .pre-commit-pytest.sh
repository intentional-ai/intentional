#!/bin/bash

# Function to run pytest in directories
run_pytest() {
  # Loop through each directory
  for dir in $1; do
    # Check if the directory exists and starts with 'intentional'
    if [[ -d "$dir" && "$dir" == intentional* ]]; then
      # Navigate to the directory, run pytest, then return to the original directory
      echo "Running pytest in $dir"
      pytest $dir || exit 1
    fi
  done
}


if [[ $1 == "all" ]]; then
  # If the first argument is 'all', find all the folders
  echo "Running pytest in ./intentional"
  pytest intentional || exit 1
  echo "Running pytest in ./intentional-core"
  pytest intentional-core || exit 1
  cd plugins/

  # If argument is 'all', find all directories starting with 'intentional'
  all_dirs=$(find . -type d -name 'intentional*' -printf '%f\n' | sort -u)
  run_pytest "$all_dirs"

else
  # Get the list of changed files and extract the directory they're in
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | awk -F'/' '{print $1}' | sort -u)
  echo "Affected main directories: $changed_dirs"
  run_pytest "$changed_dirs"

  # Otherwise, get the list of changed directories starting with 'intentional'
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^plugins/intentional' | awk -F'/' '{print $2}' | sort -u)
  echo "Affected plugins directories: $changed_dirs"
  run_pytest "$changed_dirs"
fi
