#!/bin/bash
#
# Usage:
#   ./bin/check_requirements.sh "file1.txt file2.txt"
echo "Checking requirements..."

files=$1

# if requirements/base.txt is not in changed files, there's nothing to check.
if [[ ! " ${files[@]} " =~ " requirements/base.txt " ]]; then
    echo "Base requirements did not change"
    exit 0
fi

# if ci.txt or dev.txt haven't changed, but base.txt has, the requirements were
# not upgraded properly
if [[ ! " ${files[@]} " =~ " requirements/ci.txt " ]] || [[ ! " ${files[@]} " =~ " requirements/dev.txt " ]]; then
    echo "'requirements/base.txt' was changed, but 'requirements/ci.txt' or 'requirements/dev.txt' were not."
    echo "Please update the requirements using ./bin/compile_dependencies.sh"
    exit 1
fi

echo "Seems all good"
exit 0
