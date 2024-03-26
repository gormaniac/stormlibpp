# Push Storm Packages to a Cortex

CORTEX=$1

if [ -z "$CORTEX" ]
then
    exit "Must specify the CORTEX env var!"
fi

for pkg in $(ls src/pkgs/)
do
    echo "Pushing the $pkg Storm Package to $CORTEX"
    pipenv run python3 -m synapse.tools.genpkg --push "$CORTEX" "src/pkgs/$pkg/$pkg.json"
done