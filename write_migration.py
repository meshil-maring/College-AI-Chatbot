import os

migration = (
    '-- Phase Admin-2 amendment: add missing extracted_text column to document_versions\n'
    '-- The ingestion repository (store_extracted_text / get_extracted_text) references\n'
    '-- this column, which was not present in the Phase 3.6 baseline.\n'
    '\n'
    'ALTER TABLE "public"."document_versions"\n'
    '    ADD COLUMN "extracted_text" "text";\n'
)

repo_root = os.path.dirname(os.path.abspath('write_migration.py'))
migration_dir = os.path.join(repo_root, 'supabase', 'migrations')
migration_path = os.path.join(migration_dir, '20260909000001_phase_admin_2_extracted_text_column.sql')
print(f'repo_root={repo_root}')
print(f'migration_dir={migration_dir}')

with open(migration_path, 'w', encoding='utf-8') as f:
    f.write(migration)

print(f'Written: {migration_path} ({len(migration)} bytes)')
with open(migration_path, 'r') as f:
    print('---')
    print(f.read())
    print('---')
