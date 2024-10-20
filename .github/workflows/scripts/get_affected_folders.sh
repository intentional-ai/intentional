#! /bin/bash

if git diff --quiet origin/main HEAD; then
    changed_main_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^intentional' | awk -F'/' '{print $1}' | sort -u | jq -R . | jq -s .)
    changed_plugins_dirs=$(git diff --name-only main...HEAD && git diff --name-only --cached | grep '^plugins/intentional' | awk -F'/' '{print $1"/"$2}' | sort -u | jq -R . | jq -s .)
    changed_dirs=$(jq -c -n --argjson list1 "$changed_main_dirs" --argjson list2 "$changed_plugins_dirs" '$list1 + $list2')
    echo $changed_dirs
else
    changed_dirs="$(cd plugins && ls -d intentional*/ | jq -R -s -c 'split("\n") | map(select(length > 0))')"
    echo $changed_dirs
fi
