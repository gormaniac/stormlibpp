# Copy the README files from each package to the doc folder.
# Meant to be run prior to building the sphinx docs.

for pkg in $(ls src/pkgs/)
do
    echo "Copying the README for the $pkg Storm Package"
    cp "src/pkgs/$pkg/README.md" "doc/pkgs/$pkg.md"
done