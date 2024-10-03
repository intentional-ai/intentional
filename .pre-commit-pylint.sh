#!/bin/bash

# Function to run pylint in directories
run_pylint() {
  # Loop through each unique second-level directory
  for dir in $1; do
    # Check if the second-level directory exists
    if [[ -d "$dir" ]]; then
      # Run pylint in the second-level directory
      pylint -sn -rn --rcfile=$dir/../../pyproject.toml "$dir"
    fi
  done
}

if [[ $1 == "all" ]]; then
  # If argument is 'all', find all second-level directories that match the criteria
  all_dirs=$(find . -type d | grep '^\./intentional' | grep '/src/' | grep -v ".egg-info" | awk -F'/' '{print $1"/"$2"/"$3"/"$4}' | sort -u)
  run_pylint "$all_dirs"
else
  # Otherwise, get the list of changed files and extract their second-level directories
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | grep -v '/tests' | awk -F'/' '{print $1"/"$2"/"$3}' | sort -u)
  run_pylint "$changed_dirs"
fi
