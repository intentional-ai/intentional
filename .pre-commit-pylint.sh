#!/bin/bash

# Function to run pylint in directories
run_pylint() {
  # Loop through each unique second-level directory
  for dir in $1; do
    # Check if the second-level directory exists
    if [[ -d "$dir" ]]; then
      # Run pylint in the second-level directory
      echo "Running pylint in $dir"
      pylint -sn -rn --rcfile=$dir/pyproject.toml "$dir"
    fi
  done
}



if [[ $1 == "all" ]]; then
  # If the first argument is 'all', find all the folders
  echo "Running pylint in ./intentional-core"
  pylint -sn -rn --rcfile=intentional-core/pyproject.toml intentional-core
  cd plugins/
  all_dirs=$(find . -type d | grep '^\./intentional' | grep '/src/' | grep -v ".egg-info" | awk -F'/' '{print $1"/"$2}' | sort -u)
  run_pylint "$all_dirs"
else
  # Get the list of changed files and extract the directory they're in
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | awk -F'/' '{print $1}' | sort -u)
  run_pylint "$changed_dirs"
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^plugins/intentional' | awk -F'/' '{print $1"/"$2}' | sort -u)
  run_pylint "$changed_dirs"
fi
