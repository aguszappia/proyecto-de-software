from src.core.users import service

def run():
    users = [
        {
            "email":"user1@example.com",
            "first_name":"Usuario1",        
            "last_name":"Uno",             
            "password":"12345678", 
            "role":"public"
        },
        {
            "email":"admin@example.com",
            "first_name":"Admin",
            "last_name":"Dos",
            "password":"12345678",
            "role":"admin"
        },
        {
            "email":"editor@example.com",
            "first_name":"Editor",
            "last_name":"Tres",
            "password":"12345678",
            "role":"editor"
        },
    ]
    
    for payload in users:
        ok, user, errors = service.create_user(payload)
        if not ok:
            print(f"[SEED ERROR] {payload['email']}: {errors}")
        else:
            print(f"[SEED OK] {user.email}")

    print(f"Seeds de usuarios cargada")