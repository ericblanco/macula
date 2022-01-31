#! /bin/bash

numParameters=1

cd "$(dirname $0)"

availableTargets=$(cat .git/config | grep '^\[remote ' | grep -v 'origin' | sed 's/^[^"]*"\([^"]\{1,\}\)".*$/\1/')

# Check parameters
if [ $# -ne $numParameters ]; then
    echo "error: missing required parameters (required $numParameters, got $#)" 1>&2
    echo "usage: $(basename $0) [heroku-deployment-target] [local-branch-name]" 1>&2
    #echo "e.g.:  $(basename $0) s01 next-release"
    echo "use --help to list available deployment targets" 1>&2
    exit 1
fi

if [ "$1" = '-h' ] || [ "$1" = '--help' ]; then
    echo -e "available deployment targets:\n$(echo "$availableTargets" | sed 's/.*/    &/')"
    exit 0
fi

target=$1

# Ensure that the target is recognized.
found=0
for maybeTheTarget in $availableTargets; do
    if [ "$maybeTheTarget" = "$target" ]; then
        found=1;
        break;
    fi
done

if [ "$found" = "0" ]; then
    echo "error: unrecognized target "'"'"$target"'"' 1>&2
    echo "make sure the git remote target is added, or use --help to list available deployment targets" 1>&2
    exit 2
fi

echo "[DEPLOY] [$(date)] Deploy script started at"

echo "[DEPLOY] target = $target"

branch=$(git branch --no-color | grep '^\* ' | sed 's/^\* //')
echo "[DEPLOY] Branch = $branch"

echo "[DEPLOY] git push -f $target $branch:master"
git push -f $target $branch:master

echo "[DEPLOY] [$(date)] Deploy script finished"

exit 0
