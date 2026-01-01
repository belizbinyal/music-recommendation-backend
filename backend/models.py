from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from sqlalchemy import Boolean, DateTime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String) 
    
    profile = relationship("UserProfile", back_populates="owner", uselist=False)
    # listening_history ilişkisini buraya ekleyebiliriz (opsiyonel ama iyi olur)
    listening_history = relationship("ListeningHistory", back_populates="user")
    # --- İŞTE EKSİK OLAN SATIR BU ---
    playlists = relationship("Playlist", back_populates="owner") 
    # --------------------------------
 
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
    title = Column(String, index=True)  # unique=True KALDIRDIK (Aynı isimde farklı şarkılar olabilir)
    artist = Column(String)             # Sanatçı
    genre = Column(String)              # Tür
    theme = Column(String)              # Tema/Mood (CSV'deki Theme sütunu için)
    url = Column(String, nullable=True) # İleride Spotify linki vs. gerekirse diye


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    song_id = Column(Integer, ForeignKey("songs.id"))
    
    user = relationship("User", back_populates="listening_history")
    song = relationship("Song")

#PLAYLİST KISMI EKLENENLER
class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_favorite = Column(Boolean, default=False) # Bu liste "Favorilenler" mi?

    # İlişkiler
    owner = relationship("User", back_populates="playlists")
    # Playlist içindeki şarkıları tutan ara tablo ilişkisi
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")

class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"))
    song_id = Column(Integer, ForeignKey("songs.id"))
    added_at = Column(DateTime, default=datetime.utcnow) # Sıralama için zaman damgası

    playlist = relationship("Playlist", back_populates="items")
    song = relationship("Song")

# User sınıfının içine şu satırı eklemeyi unutma (relationship):
# playlists = relationship("Playlist", back_populates="owner")