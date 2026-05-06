from web.api_app import create_app
app = create_app()
client = app.test_client()
resp = client.get('/api/plugins/spotify/playlists')
print(f"Status: {resp.status_code}")
print(f"Data: {resp.get_data(as_text=True)}")
