from src.core.users import service

def run():
    user1 = service.create_user(
        email="user1@example.com",
        first_name="Usuario1",        
        last_name="Uno",             
        password_hash="contraseña", 
        role="public"
    )
    
    user2 = service.create_user(
        email="admin@example.com",
        first_name="Admin",
        last_name="Dos",
        password_hash="contraseña",
        role="admin"
    )

    user3 = service.create_user(
        email="editor@example.com",
        first_name="Editor",
        last_name="Tres",
        password_hash="contraseña",
        role="editor"
    )
    
    print(f"Seeds de usuarios cargada")