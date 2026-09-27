#!/usr/bin/env bash
# Instaleaza Pandoc numai in workspace, fara sudo si fara modificarea sistemului.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
workspace_dir="$(cd -- "${project_dir}/../.." && pwd)"
tools_dir="${MD_PDF_TOOLS_DIR:-${workspace_dir}/.tools}"
install_dir="${tools_dir}/pandoc"
stage_dir="$(mktemp -d /tmp/pandoc-local.XXXXXX)"

cleanup() {
  rm -rf -- "${stage_dir}"
}
trap cleanup EXIT

for command_name in apt-get dpkg-deb; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'Eroare: comanda necesara lipseste: %s\n' "${command_name}" >&2
    exit 3
  fi
done

mkdir -p -- "${install_dir}"
cd -- "${stage_dir}"
printf 'Descarc Pandoc din depozitele Ubuntu (fara sudo)...\n'
apt-get download pandoc pandoc-data

for archive in ./*.deb; do
  dpkg-deb -x "${archive}" "${install_dir}"
done

pandoc_bin="${install_dir}/usr/bin/pandoc"
if [[ ! -x "${pandoc_bin}" ]]; then
  printf 'Eroare: executabilul Pandoc nu a fost extras corect.\n' >&2
  exit 4
fi

printf 'Instalare locala finalizata: %s\n' "${pandoc_bin}"
"${pandoc_bin}" --version | head -n 2
printf '\nConversie exemplu:\n  %s/md_to_pdf.sh %s/docs/RAPORT_LABORATOR_VIPRO.md\n' \
  "${script_dir}" "${project_dir}"

