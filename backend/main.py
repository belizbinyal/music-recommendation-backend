from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json 
from playlist_service import PlaylistManager
import csv
import ast
import os


# Kendi yazdığımız modülleri içeri alıyoruz
import models, schemas, crud
import ai_service 
from database import SessionLocal, engine

# Veritabanı tablolarını oluştur
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 1. BAŞLANGIÇ AYARLARI (RAPORA GÖRE GÜNCELLENDİ)
# ==========================================
@app.on_event("startup")
def startup_event():
    """
    Uygulama açıldığında veritabanı boşsa,
    Raporda belirlenen soruları veritabanına ekler.
    """
    db = SessionLocal()
    if db.query(models.Question).count() == 0:
        print("📥 Veritabanı boş, rapordaki sorular ekleniyor...")
        
        # 1. SORU: Aktivite (Rapordaki 8 Madde)
        activity_options = [
            "Ders çalışırken 📚",
            "Spor yaparken 🏃",
            "Arabada 🚗",
            "Yürürken 🚶",
            "Dinlenirken ☕",
            "Oyun oynarken 🎮",
            "Yemek yaparken 🍳",
            "Uyku öncesi 🌙"
        ]
        
        q1 = models.Question(
            question_order=1, 
            text="Genelde ne yaparken müzik dinliyorsun?", 
            type="select", 
            options=json.dumps(activity_options)
        )
        
        # 2. SORU: Müzik Türü (Rapordaki Türler)
        genre_options = [
            "Classic Rock", "Blues", "Metalcore", "Punk", 
            "J-Pop", "Anime", "Indie Folk", "Vocal Jazz",
            "Art Pop", "Avant-Garde", "Baroque Pop"
        ]
        
        q2 = models.Question(
            question_order=2,
            text="Hangi türleri seversin? (Birden fazla seçebilirsin)",
            type="multi-select",
            options=json.dumps(genre_options)
        )

        # 3. SORU: Ruh Hali (Rapordaki 7 Duygu) - GÜNCELLENDİ
        emotion_options = [
            "Mutluluk 😃",
            "Üzüntü 😔",
            "Savaş ⚔️",
            "Korku 😨",
            "Sakinlik 😌",
            "Enerji ⚡",
            "Aşk ❤️"
        ]

        q3 = models.Question(
            question_order=3,
            text="Genelde hangi duygu modunda şarkılar dinlersin?",
            type="select", 
            options=json.dumps(emotion_options) 
        )

        db.add_all([q1, q2, q3])
        db.commit()
        print("✅ Rapora uygun sorular veritabanına eklendi!")
    if db.query(models.Song).count() == 0:
        print("📥 Şarkı veritabanı hazırlanıyor...")
        
        # Senin verdiğin dosya yolu
        csv_path = r"C:\Users\Beliz\Desktop\music_project\backend\songs_labeled_FINAL_EN_TR_THEME_TFIDF_v2.csv"
        
        if not os.path.exists(csv_path):
            print(f"❌ HATA: Dosya bulunamadı -> {csv_path}")
            # Alternatif: Dosya proje klasöründeyse sadece ismini dene
            csv_path = "songs_labeled_FINAL_EN_TR_THEME_TFIDF_v2.csv"

        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    songs_to_add = []
                    
                    print(f"📂 CSV Okunuyor: {csv_path}")
                    
                    for row in reader:
                        # --- VERİ TEMİZLEME ---
                        
                        # 1. Sanatçı İsmi Temizliği (['Artist'] -> Artist)
                        artist_raw = row.get("artists", "Bilinmiyor") # CSV'deki sütun adı 'artists' ise
                        try:
                            if artist_raw.startswith("['"):
                                artist_list = ast.literal_eval(artist_raw)
                                artist_clean = ", ".join(artist_list)
                            else:
                                artist_clean = artist_raw
                        except:
                            artist_clean = artist_raw

                        # 2. Sütun Eşleştirme
                        # CSV başlıklarının tam olarak böyle olduğunu varsayıyorum.
                        # Değilse row["..."] içindeki kısımları CSV'ne göre değiştir.
                        song = models.Song(
                            title=row.get("name", "İsimsiz"),   # CSV'de 'name' mi 'track_name' mi kontrol et
                            artist=artist_clean,
                            genre=row.get("genre", "Genel"),
                            theme=row.get("THEME", None) or row.get("emotion_final_adjusted", None) # Hangi sütun varsa
                        )
                        songs_to_add.append(song)
                    
                    # Veritabanına kaydet
                    db.add_all(songs_to_add)
                    db.commit()
                    print(f"✅ Başarılı: {len(songs_to_add)} şarkı veritabanına yüklendi!")
                    
            except Exception as e:
                print(f"❌ Şarkılar yüklenirken hata oluştu: {e}")
        else:
            print("⚠️ CSV dosyası bulunamadığı için şarkı yüklenemedi.")
    db.close()


# ==========================================
# 2. API ENDPOINTLERİ
# ==========================================

@app.get("/")
def home():
    return {"message": "Sistem Aktif! /docs adresine giderek test et."}

# --- SORULARI GETİR ---
@app.get("/content/questions", response_model=List[schemas.Question])
def get_questions(db: Session = Depends(get_db)):
    """Frontend'in ekrana çizeceği soruları buradan çekiyoruz"""
    return db.query(models.Question).order_by(models.Question.question_order).all()

# --- KULLANICI KAYIT ---
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı.")
    return crud.create_user(db=db, user=user)

# --- PROFİL OLUŞTURMA (NLP BURADA) ---
@app.post("/users/{user_id}/profile/", response_model=schemas.Profile)
def create_profile_for_user(
    user_id: int, 
    profile: schemas.ProfileCreate, 
    db: Session = Depends(get_db)
):
    # 1. ÇORBA YAPMA (SOUP)
    # 3. sorunun cevabı artık seçmeli geldiği için onu da metne ekliyoruz.
    combined_text = (
        f"Aktivite: {profile.hobbies}. "
        f"Sevdiği Türler: {profile.favorite_genres}. "
        f"Ruh Hali: {profile.mood_description}"
    )

    # 2. NLP ile Vektör Hesapla
    vector_list = ai_service.get_mood_vector(combined_text)
    
    # 3. Vektörü String'e çevir
    vector_json_str = json.dumps(vector_list)
    
    print(f"🤖 NLP Vektörü Oluştu. Boyut: {len(vector_list)}")

    # 4. Kaydet
    return crud.create_user_profile(
        db=db, 
        profile=profile, 
        user_id=user_id,
        mood_vector_json=vector_json_str 
    )

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return db_user

# --- ÖNERİ SİSTEMİ (Şimdilik boş döner, sonra dataset eklenince çalışacak) ---
import recommendation 
@app.get("/users/{user_id}/recommendations/")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    matches = recommendation.get_similar_users(db, current_user_id=user_id)
    return {
        "user_id": user_id,
        "recommended_users": matches
    }

# --- PLAYLIST ENDPOINTLERİ ---

@app.post("/users/{user_id}/playlists/", response_model=schemas.PlaylistOut)
def create_playlist(user_id: int, playlist: schemas.PlaylistCreate, db: Session = Depends(get_db)):
    """Yeni özel playlist oluşturur (Max 40 kontrolü var)"""
    manager = PlaylistManager(db)
    return manager.create_playlist(user_id=user_id, name=playlist.name, is_favorite=False)

@app.get("/users/{user_id}/playlists/", response_model=List[schemas.PlaylistOut])
def get_playlists(user_id: int, db: Session = Depends(get_db)):
    """Kullanıcının tüm playlistlerini getirir"""
    manager = PlaylistManager(db)
    return manager.get_user_playlists(user_id)

@app.get("/users/{user_id}/favorites/", response_model=schemas.PlaylistOut)
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    """Sadece favorilenler listesini döner"""
    manager = PlaylistManager(db)
    return manager.get_favorites_playlist(user_id)

# --- ŞARKI EKLEME / ÇIKARMA ---

@app.post("/playlists/{playlist_id}/songs/{song_id}")
def add_song_to_playlist(playlist_id: int, song_id: int, db: Session = Depends(get_db)):
    """Bir playliste şarkı ekler (Max 500 kontrolü var)"""
    manager = PlaylistManager(db)
    manager.add_song_to_playlist(playlist_id, song_id)
    return {"message": "Şarkı playliste eklendi."}

@app.delete("/playlists/{playlist_id}/songs/{song_id}")
def remove_song_from_playlist(playlist_id: int, song_id: int, db: Session = Depends(get_db)):
    """Bir playlistten şarkı siler"""
    manager = PlaylistManager(db)
    return manager.remove_song_from_playlist(playlist_id, song_id)

# --- FAVORİLEME BUTONU ---

@app.post("/users/{user_id}/favorites/toggle/{song_id}")
def toggle_favorite_song(user_id: int, song_id: int, db: Session = Depends(get_db)):
    """Kalp butonuna basınca çalışır. Varsa siler, yoksa en üste ekler."""
    manager = PlaylistManager(db)
    return manager.toggle_favorite(user_id, song_id)