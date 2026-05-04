"""config_normalization

Revision ID: a1b2c3d4e5f6
Revises: 8f6df972e61a
Create Date: 2026-05-04 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8f6df972e61a'
branch_labels = None
depends_on = None

def _flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def upgrade() -> None:
    # 1. Drop Legacy Tables
    op.execute("DROP TABLE IF EXISTS config_kvs")
    op.execute("DROP TABLE IF EXISTS account_metadata")

    # 2. Update `services` Table
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.add_column(sa.Column('namespace', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('plugin_id', sa.Integer(), nullable=True))
    
    op.execute("UPDATE services SET namespace = name")
    
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.alter_column('namespace', existing_type=sa.String(), nullable=False)

    # 3. Update `accounts` and `account_tokens`
    bind = op.get_bind()
    insp = sa.inspect(bind)
    accounts_cols = [c['name'] for c in insp.get_columns('accounts')]
    
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        if 'plugin_id' in accounts_cols:
            batch_op.drop_column('plugin_id')
        if 'display_name' in accounts_cols:
            batch_op.drop_column('display_name')

    # 4. Create `system_settings` Table
    op.create_table('system_settings',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )

    # 5. Create Quality Profile Tables
    op.create_table('quality_profiles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('prefer_max_quality', sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('quality_profile_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['quality_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Data Migration & Cleanup Hook
    from core.settings import config_manager
    config_path = config_manager.config_dir / 'config.json'
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            
        settings_to_migrate = ['manager', 'metadata_enhancement', 'file_organization', 'playlist_sync', 'discovery_pool']
        system_settings_data = []
        
        for root_key in settings_to_migrate:
            if root_key in config_data:
                flattened = _flatten_dict({root_key: config_data[root_key]})
                for k, v in flattened.items():
                    system_settings_data.append({'key': k, 'value': str(v) if not isinstance(v, (dict, list)) else json.dumps(v)})
                del config_data[root_key]
                
        if 'ui' in config_data and isinstance(config_data['ui'], dict) and 'beta_plugin_ui' in config_data['ui']:
            system_settings_data.append({'key': 'ui.beta_plugin_ui', 'value': str(config_data['ui']['beta_plugin_ui']) if not isinstance(config_data['ui']['beta_plugin_ui'], (dict, list)) else json.dumps(config_data['ui']['beta_plugin_ui'])})
            del config_data['ui']['beta_plugin_ui']

        if 'safe_mode' not in config_data:
            config_data['safe_mode'] = False

        if system_settings_data:
            op.bulk_insert(
                sa.table('system_settings',
                    sa.column('key', sa.String),
                    sa.column('value', sa.Text)
                ),
                system_settings_data
            )
            
        # Quality Profiles
        quality_profiles_data = []
        quality_profile_steps_data = []
        
        if 'quality_profiles' in config_data:
            for profile_id, profile in config_data['quality_profiles'].items():
                quality_profiles_data.append({
                    'id': profile_id,
                    'name': profile.get('name', profile_id),
                    'prefer_max_quality': profile.get('prefer_max_quality', False)
                })
                
                formats = profile.get('formats', [])
                for f in formats:
                    priority = f.get('priority', 1)
                    quality_profile_steps_data.append({
                        'profile_id': profile_id,
                        'priority': priority,
                        'rules': json.dumps(f)
                    })
            del config_data['quality_profiles']
            
            if quality_profiles_data:
                op.bulk_insert(
                    sa.table('quality_profiles',
                        sa.column('id', sa.String),
                        sa.column('name', sa.String),
                        sa.column('prefer_max_quality', sa.Boolean)
                    ),
                    quality_profiles_data
                )
            if quality_profile_steps_data:
                op.bulk_insert(
                    sa.table('quality_profile_steps',
                        sa.column('profile_id', sa.String),
                        sa.column('priority', sa.Integer),
                        sa.column('rules', sa.JSON)
                    ),
                    quality_profile_steps_data
                )

        # Plugins / Providers
        service_config_data = []
        for legacy_key in ['providers', 'plugins']:
            if legacy_key in config_data:
                for plugin_id, plugin_conf in config_data[legacy_key].items():
                    res = bind.execute(sa.text("SELECT id FROM services WHERE name = :name"), {'name': plugin_id}).fetchone()
                    if res:
                        svc_id = res[0]
                        flattened = _flatten_dict(plugin_conf)
                        for k, v in flattened.items():
                            service_config_data.append({
                                'service_id': svc_id,
                                'config_key': k,
                                'config_value': str(v) if not isinstance(v, (dict, list)) else json.dumps(v),
                                'is_sensitive': 0
                            })
                del config_data[legacy_key]

        if service_config_data:
            op.bulk_insert(
                sa.table('service_config',
                    sa.column('service_id', sa.Integer),
                    sa.column('config_key', sa.String),
                    sa.column('config_value', sa.Text),
                    sa.column('is_sensitive', sa.Integer)
                ),
                service_config_data
            )
            
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)

def downgrade() -> None:
    op.drop_table('quality_profile_steps')
    op.drop_table('quality_profiles')
    op.drop_table('system_settings')
    
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_column('namespace')
        batch_op.drop_column('plugin_id')
