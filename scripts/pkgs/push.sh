# Push Storm Packages to a Cortex
#
# This builds the Storm packages currently in source and pushes them to the specified Cortex.
#
# For production deployment, it's better to use the json files in the repo's releases.

CORTEX=$1

if [ -z "$CORTEX" ]
then
    exit "Must specify the CORTEX env var!"
fi

mkdir -p dist
make build-storm

for pkg in $(ls src/pkgs/)
do
    echo "Pushing the $pkg Storm Package to $CORTEX"
    pipenv run python3 -m synapse.tools.genpkg --push "$CORTEX" "dist/$pkg.json"
done