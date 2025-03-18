#!/bin/sh

# Determine the base ref or fallback to the last commit
if [ -n "$GITHUB_BASE_REF" ]; then
    BASE_REF="origin/$GITHUB_BASE_REF"
else
    BASE_REF="HEAD^"  # Compare with the previous commit on main branch
fi

git fetch --all

# Get the list of files that were changed between the base branch and the current commit
CHANGED_FILES=$(git diff --name-only $BASE_REF...HEAD)
if echo "$CHANGED_FILES" | grep -q "$1"; then
    echo "Files were changed!"
    echo "any_changed=true" >> $GITHUB_OUTPUT
else
    echo "No changes detected"
    echo "any_changed=false" >> $GITHUB_OUTPUT
fi
