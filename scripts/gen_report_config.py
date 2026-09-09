"""gen_report_config.py - generate report label translations + display config.

Reads the form XMLs (via scale_meta.py, the single source of truth) and:

1. Appends missing English translation keys to translations/messages-en.properties
   inside a clearly marked generated block:
     report.<form>._title        -> human scale title
     report.<form>.<group path>  -> group/section labels (age bands, domains)
     report.<form>.<field path>  -> question/field labels from the form body

   Existing keys are NEVER modified - the curated entries already in
   messages-en.properties (results, summary labels, MoCA questions) stay
   authoritative. Only keys missing entirely are added.

2. Injects the 'report_display' config into app_settings/base_settings.json
   and the compiled app_settings.json, preserving every other setting. This
   config drives the cht-core report patch: hide internal fields, resolve
   choice labels, join chronological-age rows, render note fields, suppress
   empty values.

Usage:
  python scripts/gen_report_config.py             # apply
  python scripts/gen_report_config.py --check     # verify only (exit 1 = drift)
  python scripts/gen_report_config.py --dry-run   # print what would change
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scale_meta import SCALES, get_scale_meta, JOIN_FIELDS, build_report_display_config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESSAGES_PATH = os.path.join(REPO_ROOT, 'translations', 'messages-en.properties')
BASE_SETTINGS_PATH = os.path.join(REPO_ROOT, 'app_settings', 'base_settings.json')
COMPILED_SETTINGS_PATH = os.path.join(REPO_ROOT, 'app_settings.json')

MARKER_BEGIN = '# ==== generated scale report labels (scripts/gen_report_config.py) ===='
MARKER_END = '# ==== end generated scale report labels ===='
CRLF = '\r\n'


def clean_label(label):
    return ' '.join(label.split())


def desired_keys_for(form):
    """Ordered [(key, label)] for one scale, from the form definition."""
    meta = get_scale_meta(form)
    join_labels = {j['target']: clean_label(j['label'])
                   for j in JOIN_FIELDS[form]}
    prefix = f'report.{form}.'
    entries = [(f'{prefix}_title', meta['title'])]
    for item in meta['flat']:
        path = item['path']
        if not path:
            continue
        if path in join_labels:
            label = join_labels[path]
        else:
            label = clean_label(item['label'])
        if label:
            entries.append((prefix + path, label))
    return entries


def split_messages(content):
    """Split file content into (before, block_body, after).

    Keys OUTSIDE the generated block are curated and never touched.
    Keys inside the block are owned by this script and fully regenerated
    on every run (idempotent).
    """
    lines = content.splitlines(keepends=True)
    begin_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == MARKER_BEGIN:
            begin_idx = i
        if line.strip() == MARKER_END:
            end_idx = i
            break
    if begin_idx is not None and end_idx is not None:
        before = ''.join(lines[:begin_idx])
        after = ''.join(lines[end_idx + 1:])
        return before, ''.join(lines[begin_idx:end_idx + 1]), after
    return content, None, ''


def keys_in(content):
    keys = set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if '=' in stripped:
            keys.add(stripped.split('=', 1)[0].strip())
    return keys


def build_generated_block(per_form_entries):
    parts = [MARKER_BEGIN + CRLF]
    for form in SCALES:
        parts.append(f'# ---- {SCALES[form]["title"]} ----' + CRLF)
        for key, label in per_form_entries[form]:
            parts.append(f'{key} = {label}' + CRLF)
    parts.append(MARKER_END + CRLF)
    return ''.join(parts)


def load_messages():
    with open(MESSAGES_PATH, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def update_messages(dry_run=False):
    content = load_messages()
    before, block, after = split_messages(content)
    curated = keys_in(before) | keys_in(after)
    per_form = {}
    total = 0
    for form in SCALES:
        entries = [(key, label) for key, label in desired_keys_for(form)
                   if key not in curated]
        per_form[form] = entries
        total += len(entries)
    new_block = build_generated_block(per_form)
    new_content = before + new_block + after
    if not dry_run and new_content != content:
        with open(MESSAGES_PATH, 'w', encoding='utf-8', newline='') as f:
            f.write(new_content)
    return total, per_form


def update_json_setting(path, config, dry_run=False):
    with open(path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    if settings.get('report_display') == config:
        return False
    if dry_run:
        return True
    settings['report_display'] = config
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate scale report translations + display config')
    parser.add_argument('--check', action='store_true',
                        help='exit 1 if the files need regeneration')
    parser.add_argument('--dry-run', action='store_true',
                        help='report changes without writing files')
    args = parser.parse_args()

    count, per_form = update_messages(dry_run=True)
    config = build_report_display_config()
    base_changed = update_json_setting(BASE_SETTINGS_PATH, config, dry_run=True)
    compiled_changed = update_json_setting(COMPILED_SETTINGS_PATH, config,
                                           dry_run=True)

    if args.dry_run:
        print(f'message keys in generated block: {count}')
        for form in SCALES:
            print(f'  {form}: {len(per_form[form])} keys')
        print(f'base_settings.json report_display: '
              f'{"would update" if base_changed else "up to date"}')
        print(f'app_settings.json report_display: '
              f'{"would update" if compiled_changed else "up to date"}')
        return

    if args.check:
        ok = count == len(per_form_expected()) and not base_changed \
            and not compiled_changed
        if not ok:
            print('drift detected: run scripts/gen_report_config.py')
            print(f'  generated-block keys: {count} '
                  f'(expected {len(per_form_expected())})')
            print(f'  base_settings.json needs update: {base_changed}')
            print(f'  app_settings.json needs update: {compiled_changed}')
            sys.exit(1)
        print('report config up to date')
        return

    update_messages(dry_run=False)
    update_json_setting(BASE_SETTINGS_PATH, config)
    update_json_setting(COMPILED_SETTINGS_PATH, config)
    print(f'generated block: {count} message keys in '
          f'{os.path.relpath(MESSAGES_PATH, REPO_ROOT)}')
    for form in SCALES:
        print(f'  {form}: {len(per_form[form])} keys')
    print(f'report_display written to app_settings/base_settings.json '
          f'and app_settings.json')


def per_form_expected():
    """Key count the generated block should contain per form."""
    content = load_messages()
    before, _, after = split_messages(content)
    curated = keys_in(before) | keys_in(after)
    return [key for form in SCALES for key, _ in desired_keys_for(form)
            if key not in curated]


if __name__ == '__main__':
    main()
