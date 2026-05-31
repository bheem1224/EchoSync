import sys

from web.app import create_app
app = create_app()
app.testing = True

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = '1'
        sess['is_authenticated'] = True
    resp = client.get('/api/system/plugins/store')
    if resp.status_code == 200:
        data = resp.get_json()
        for p in data.get('plugins', []):
            print(f"{p.get('name')}: {p.get('_installed')}")
    else:
        print(f"Failed with status: {resp.status_code}")
