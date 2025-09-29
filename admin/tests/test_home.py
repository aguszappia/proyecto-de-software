from src.web import create_app

app = create_app(env="testing")
client = app.test_client()

def test_home():
    response = client.get('/')
    assert response.status_code == 200
    assert b"<h1>Inicio</h1>" in response.data