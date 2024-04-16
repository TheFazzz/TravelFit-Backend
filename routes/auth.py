import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import uuid
from psycopg2 import IntegrityError
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

from models.models import *
from services.database import *
from utils.settings import get_blob_connection_string

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")  # Get the secret key
ALGORITHM = os.getenv("ALGORITHM")  # Get the algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))  # Get the expiration time

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return password_context.hash(password)

def verify_password(plain_password, hashed_password):
    return password_context.verify(plain_password, hashed_password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):  
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )  
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    
    except JWTError:
        raise credentials_exception   

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

@router.post("/login")
async def login_for_access_token(
    user: LoginRequest, 
    db: tuple = Depends(get_db_connection)
):
    connection, cursor = db
    try:
        # Authenticate the user
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        user_data = cursor.fetchone()
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        stored_user = {
            "id": user_data[0],
            "firstName": user_data[1],
            "lastName": user_data[2],
            "email": user_data[3],
            "password_hash": user_data[4],
        }

        if not verify_password(user.password, stored_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = stored_user["id"]
        first_name = stored_user["firstName"]
        last_name = stored_user["lastName"]

        # Determine the user's role and fetch gym_id if necessary
        role = "user"
        gym_id = None
        cursor.execute("SELECT id FROM Admins WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            role = "admin"
        else:
            cursor.execute("SELECT gym_id FROM Gym_Admins WHERE user_id = %s", (user_id,))
            gym_admin_data = cursor.fetchone()
            if gym_admin_data:
                role = "gym"
                gym_id = gym_admin_data[0]

        # Create access token
        token_data = {
            "sub": str(user_id),
            "firstName": first_name,
            "lastName": last_name,
            "role": role
        }
        if gym_id:
            token_data["gym_id"] = gym_id

        access_token = await create_access_token(data=token_data)

        return_data = {"access_token": access_token, "token_type": "bearer", "role": role}
        if gym_id:
            return_data["gym_id"] = gym_id

        return return_data
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        connection.close()


@router.post("/logout")
async def logout():
    # For a logout endpoint with JWT, you don't need to do anything on the server side
    # Instruct the client(front-end) to discard the access token
    return {"message": "Logout successful"}



@router.post("/register")
async def register(
    req: RegisterRequest,
    db: tuple = Depends(get_db_connection)
):
    connection, cursor = db
    hashed_password = hash_password(req.password)
    try:
        cursor.execute(
            """
            INSERT INTO users (firstName, lastName, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (req.first_name, req.last_name, req.email, hashed_password),
        )
        user_id = cursor.fetchone()[0]  # Get the inserted user ID
        
        connection.commit()  

        return ReturnIdResponse(id=user_id)
    
    except IntegrityError as e:
        # Check if the error is due to a duplicate email
        if 'unique constraint "users_email_key"' in str(e):
            raise HTTPException(status_code=400, detail="Email is already in use")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/users/{user_id}/profile-photo")
async def upload_profile_photo(
    user_id: int,
    profile_photo: UploadFile = File(...),
    user = Depends(get_current_user),
    db: tuple = Depends(get_db_connection)
):
    if user['role'] not in ['admin', 'user']:
        raise HTTPException(status_code=403, detail="Access denied: Unauthorized role")

    if user['role'] == 'user' and user['sub'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot update other users info")
    
    connection, cursor = db
    try:
        # Check if user already has a profile photo
        cursor.execute(
            """
            SELECT profile_photo FROM users WHERE id = %s
            """,
            (user_id,)
        )
        current_profile_photo_url = cursor.fetchone()[0]

        blob_connection_string = get_blob_connection_string()
        container_name = f"profile-photos"
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Delete the old profile photo from blob storage if it exists
        if current_profile_photo_url:
            blob_name = current_profile_photo_url.split("/")[-1]
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.delete_blob()

        # Generate a unique filename for the profile photo
        unique_filename = f"{user_id}_{uuid.uuid4().hex}{os.path.splitext(profile_photo.filename)[1]}"
        
        # Check if the container exists, if not create one
        if not container_client.exists():
            container_client.create_container()

        blob_client = container_client.get_blob_client(unique_filename)
        blob_client.upload_blob(profile_photo.file)
        profile_photo_url = f"https://travelfitstorage.blob.core.windows.net/{container_name}/{unique_filename}"
        
        # Update the user record with the profile photo URL
        cursor.execute(
            """
            UPDATE users
            SET profile_photo = %s
            WHERE id = %s
            """,
            (profile_photo_url, user_id),
        )
        
        connection.commit()  # Commit the transaction

        return {"message": "Profile photo uploaded successfully", "profile_photo_url": profile_photo_url}
    
    finally:
        cursor.close()
        connection.close()

@router.put("/users/{user_id}")
async def update_user_info(
    user_id: int,
    user_info: UpdateUserInfo,
    user = Depends(get_current_user),
    db: tuple = Depends(get_db_connection)
):
    if user['role'] not in ['admin', 'user']:
        raise HTTPException(status_code=403, detail="Access denied: Unauthorized role")

    if user['role'] == 'user' and user['sub'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot update other users info")

    connection, cursor = db
    try:
         # Check if the user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Construct the UPDATE query based on provided fields
        update_query = "UPDATE users SET"
        update_values = []
        if user_info.firstName:
            update_query += " firstName = %s,"
            update_values.append(user_info.firstName)
        if user_info.lastName:
            update_query += " lastName = %s,"
            update_values.append(user_info.lastName)
        if user_info.email:
            update_query += " email = %s,"
            update_values.append(user_info.email)
        

        # Remove trailing comma and space from the query
        update_query = update_query.rstrip(",")

        # Add the WHERE clause
        update_query += " WHERE id = %s"
        update_values.append(user_id)

        # Execute the UPDATE query
        cursor.execute(update_query, update_values)
        connection.commit()

        return {"message": "User information updated successfully"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user information")

    finally:
        cursor.close()
        connection.close()

@router.get("/users/{user_id}")
def get_user_info(
    user_id: int,
    user = Depends(get_current_user),
    db: tuple = Depends(get_db_connection)
):
    if user['role'] not in ['admin', 'user']:
        raise HTTPException(status_code=403, detail="Access denied: Unauthorized role")

    if user['role'] == 'user' and user['sub'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot view other users info")

    connection, cursor = db
    try:
        cursor.execute(
            """
            SELECT firstName, lastName, email, profile_photo
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        
        user = cursor.fetchone()
        
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        connection.commit()

        user_info = {
            "first_name": user[0],
            "last_name": user[1],
            "email": user[2],
            "profile_photo": user[3] if user[3] is not None else None
        }
        
        return user_info
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch user info")

    finally:
        cursor.close()
        connection.close()

@router.get("/users")
async def all_users(
    user = Depends(get_current_user),
    db: tuple = Depends(get_db_connection)
):
    if user['role'] not in ['admin']:
        raise HTTPException(status_code=403, detail="Access denied: Unauthorized role")

    connection, cursor = db
    
    try:
        cursor.execute(
            """
            SELECT * FROM users
            """
        )
        users = cursor.fetchall()

        # Convert the result to a list of dictionaries
        user_list = [
            {
                "id": user[0],
                "firstName": user[1],
                "lastName": user[2],
                "email": user[3],
                "password_hash": user[4]
            }
            for user in users
        ]

        return JSONResponse(content={"users": user_list}, status_code=200)

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
