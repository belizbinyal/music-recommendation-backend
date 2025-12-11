from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String) 
    
    profile = relationship("UserProfile", back_populates="owner", uselist=False)
    # listening_history ilişkisini buraya ekleyebiliriz (opsiyonel ama iyi olur)
    listening_history = relationship("ListeningHistory", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) 
    
    age = Column(Integer)
    location = Column(String)
    hobbies = Column(String)
    favorite_genres = Column(String)
    mood_description = Column(String) 
    mood_vector = Column(String) # Vektör verisi

    owner = relationship("User", back_populates="profile")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)       
    question_order = Column(Integer)
    type = Column(String)       
    options = Column(String)    

# --- YENİ EKLENEN TABLOLAR ---

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True) 
    # İstersen artist, genre vs. eklenebilir ama şu anlık title yeterli

class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    song_id = Column(Integer, ForeignKey("songs.id"))
    
    user = relationship("User", back_populates="listening_history")
    song = relationship("Song")