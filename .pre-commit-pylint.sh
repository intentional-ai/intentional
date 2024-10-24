#!/bin/bash

# Function to run pylint in directories
run_pylint() {
  # Loop through each unique second-level directory
  for dir in $1; do
    # Check if the second-level directory exists
    if [[ -d "$dir" ]]; then
      # Run pylint in the second-level directory
      echo "Running pylint in $dir"
      pylint -sn -rn --rcfile=$dir/pyproject.toml "$dir"/src || exit 1
    fi
  done
}

if [[ $1 == "all" ]]; then
  # If the first argument is 'all', find all the folders
  echo "Running pylint in ./intentional"
  pylint -sn -rn --rcfile=intentional/pyproject.toml intentional || exit 1
  echo "Running pylint in ./intentional-core"
  pylint -sn -rn --rcfile=intentional-core/pyproject.toml intentional-core || exit 1
  cd plugins/
  all_dirs=$(find . -type d | grep '^\./intentional' | grep '/src/' | grep -v ".egg-info" | awk -F'/' '{print $1"/"$2}' | sort -u)
  run_pylint "$all_dirs"

else
  # Get the list of changed files and extract the directory they're in
  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | awk -F'/' '{print $1}' | sort -u)
  echo "Affected main directories: $changed_dirs"
  run_pylint "$changed_dirs"

  changed_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^plugins/intentional' | awk -F'/' '{print $1"/"$2}' | sort -u)
  echo "Affected plugin directories: $changed_dirs"
  run_pylint "$changed_dirs"
fi
