# Build Storm Packages

for pkg in $(ls src/pkgs/)
do
    echo "Building the $pkg Storm Package"
    fileBase="src/pkgs/$pkg/$pkg"
    pipenv run python3 -m synapse.tools.genpkg --save "$fileBase.json" "$fileBase.yaml"
done