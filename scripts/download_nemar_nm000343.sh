#!/usr/bin/env bash
set -euo pipefail

dataset_version="v1.0.3"
dataset_root="data/nm000343-${dataset_version}"
manifest_path="data/nm000343-manifest.json"

mkdir -p "${dataset_root}"

if [[ ! -f "${manifest_path}" ]]; then
  curl -L --fail --retry 3 \
    -o "${manifest_path}" \
    "https://data.nemar.org/nm000343/${dataset_version}/manifest.json"
fi

jq -r '.[] | select(.path | startswith("sourcedata/") | not) | [.bytes_url, .path] | @tsv' "${manifest_path}" |
while IFS=$'\t' read -r source_url relative_path; do
  destination="${dataset_root}/${relative_path}"
  mkdir -p "$(dirname "${destination}")"
  curl -L --fail --retry 3 -C - -o "${destination}" "${source_url}"
done
