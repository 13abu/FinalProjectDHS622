import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from final_project.utilities.security_logic import add_credentials

if __name__ == "__main__":
    email = input("Email: ")
    password = input("Password: ")
    add_credentials(email, password)
    print(f"Credentials added for {email}")