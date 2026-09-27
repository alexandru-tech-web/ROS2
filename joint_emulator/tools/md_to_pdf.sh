#!/usr/bin/env bash
# Conversie reproductibila Markdown -> PDF pentru documentatia ViPRO.
# Dependinte: Pandoc (de sistem sau instalat local de setup_md_to_pdf.sh)
# si Chromium pentru tiparirea HTML-ului intermediar.

set -euo pipefail

usage() {
  cat <<'EOF'
Utilizare:
  ./tools/md_to_pdf.sh <document.md> [document.pdf]

Exemplu:
  ./tools/md_to_pdf.sh docs/RAPORT_LABORATOR_VIPRO.md

Daca destinatia lipseste, PDF-ul este creat langa fisierul Markdown.
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
workspace_dir="$(cd -- "${project_dir}/../.." && pwd)"
local_tools_dir="${MD_PDF_TOOLS_DIR:-${workspace_dir}/.tools}"

input_arg="$1"
if [[ ! -f "${input_arg}" ]]; then
  printf 'Eroare: fisierul Markdown nu exista: %s\n' "${input_arg}" >&2
  exit 2
fi

input_file="$(realpath -- "${input_arg}")"
input_dir="$(dirname -- "${input_file}")"
input_name="$(basename -- "${input_file}")"

if [[ $# -eq 2 ]]; then
  output_file="$(realpath -m -- "$2")"
else
  output_file="${input_file%.*}.pdf"
fi

if command -v pandoc >/dev/null 2>&1; then
  pandoc_bin="$(command -v pandoc)"
  pandoc_data_args=()
elif [[ -x "${local_tools_dir}/pandoc/usr/bin/pandoc" ]]; then
  pandoc_bin="${local_tools_dir}/pandoc/usr/bin/pandoc"
  pandoc_data_dir="${local_tools_dir}/pandoc/usr/share/pandoc/data"
  pandoc_data_args=(--data-dir="${pandoc_data_dir}")
else
  printf 'Eroare: Pandoc nu este disponibil. Ruleaza o singura data:\n' >&2
  printf '  %s/setup_md_to_pdf.sh\n' "${script_dir}" >&2
  exit 3
fi

if command -v chromium >/dev/null 2>&1; then
  chromium_bin="$(command -v chromium)"
elif [[ -x /snap/bin/chromium ]]; then
  chromium_bin=/snap/bin/chromium
else
  printf 'Eroare: Chromium nu este instalat; este necesar pentru generarea PDF.\n' >&2
  exit 3
fi

mkdir -p -- "$(dirname -- "${output_file}")"
build_dir="$(mktemp -d "${workspace_dir}/md-to-pdf.XXXXXX")"
build_html="${build_dir}/document.html"
build_pdf="${build_dir}/document.pdf"
build_log="${output_file}.build.log"

cleanup() {
  rm -rf -- "${build_dir}"
}
trap cleanup EXIT

printf 'Convertesc: %s\n' "${input_file}"
printf 'Destinatie: %s\n' "${output_file}"

set +e
(
  cd -- "${input_dir}"
  MD_PDF_SOURCE_DIR="${input_dir}" "${pandoc_bin}" \
    "${pandoc_data_args[@]}" \
    --from='markdown+pipe_tables+task_lists+strikeout+tex_math_dollars+tex_math_single_backslash+raw_tex' \
    --to=html5 \
    --standalone \
    --embed-resources \
    --mathml \
    --lua-filter="${script_dir}/pdf/absolute_file_links.lua" \
    --table-of-contents \
    --toc-depth=3 \
    --resource-path="${input_dir}:${project_dir}" \
    --css="${script_dir}/pdf/academic.css" \
    --metadata=lang:ro-RO \
    "${input_name}" \
    --output="${build_html}"

  "${chromium_bin}" \
    --headless \
    --disable-gpu \
    --no-sandbox \
    --no-pdf-header-footer \
    --print-to-pdf="${build_pdf}" \
    "file://${build_html}"
  [[ -s "${build_pdf}" ]] || { printf 'Chromium nu a produs fisierul PDF.\n' >&2; exit 5; }
) >"${build_log}" 2>&1
status=$?
set -e

if [[ ${status} -ne 0 ]]; then
  printf 'Conversia a esuat. Jurnal: %s\n' "${build_log}" >&2
  tail -n 40 -- "${build_log}" >&2
  exit "${status}"
fi

mv -- "${build_pdf}" "${output_file}"
rm -f -- "${build_log}"
printf 'PDF creat: %s\n' "${output_file}"

