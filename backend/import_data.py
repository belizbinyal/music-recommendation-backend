import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, schemas, crud, ai_service
import json
import os
import sys

# Veritabanı tablolarını oluştur
models.Base.metadata.create_all(bind=engine)

def veri_yukle_baslat():
    # --- AYARLAR ---
    csv_dosya_adi = "kullancı veri setimiz 23.12.csv"
    
    # Dosya kontrolü
    if not os.path.exists(csv_dosya_adi):
        print(f"❌ HATA: '{csv_dosya_adi}' bulunamadı!")
        return

    print("📊 Veri seti okunuyor...")
    try:
        df = pd.read_csv(csv_dosya_adi, encoding='utf-8')
        df.columns = df.columns.str.strip() # Sütun isimlerindeki boşlukları temizle
    except Exception as e:
        print(f"❌ CSV okuma hatası: {e}")
        return

    db = SessionLocal()
    print(f"🚀 Toplam {len(df)} satır veri işlenecek...")

    basarili = 0
    hatali = 0
    
    for index, row in df.iterrows():
        # EN KRİTİK NOKTA: db_user değişkenini burada güvenli başlatıyoruz
        db_user = None 

        try:
            # 1. Verileri Hazırla
            email = str(row['Email']).strip()
            username = str(row['Nickname']).strip()
            password = str(row['Şifre']).strip()
            
            # NLP Alanları
            activity = str(row['Ne Yaparken Dinlediği'])
            genres = str(row['Şarkı Türü'])
            mood = str(row['Şarkı Duygusu'])

            # 2. Kullanıcı Var mı Kontrol Et
            existing_user = crud.get_user_by_email(db, email=email)
            
            if existing_user:
                print(f"⚠️ Satır {index}: {email} zaten kayıtlı. Atlanıyor...")
                continue # Döngünün başına dön
            
            # 3. Kullanıcı Yoksa Oluştur
            print(f"➕ Yeni kullanıcı oluşturuluyor: {username}")
            user_in = schemas.UserCreate(username=username, email=email, password=password)
            
            # Veritabanına kaydet
            db_user = crud.create_user(db=db, user=user_in)
            db.flush() # ID oluşsun diye zorla

            # Hata Kontrolü: Eğer db_user hala yoksa hata fırlat
            if db_user is None:
                raise ValueError("Kullanıcı oluşturulamadı (db_user None döndü).")

            # 4. Profil ve Vektör İşlemleri
            combined_text = f"Aktivite: {activity}. Sevdiği Türler: {genres}. Ruh Hali: {mood}"
            vector_list = ai_service.get_mood_vector(combined_text)
            
            # Yaş verisi bazen boş gelebilir, kontrol et
            try: 
                age_val = int(row['Yaş'])
            except: 
                age_val = 18

            profile_in = schemas.ProfileCreate(
                age=age_val,
                location="İstanbul",
                hobbies=activity,
                favorite_genres=genres,
                mood_description=mood
            )

            # Profili kaydet
            crud.create_user_profile(
                db=db, 
                profile=profile_in, 
                user_id=db_user.id, 
                mood_vector_json=json.dumps(vector_list)
            )
            
            # 5. Geçmiş Şarkıları Ekle
            if 'Geçmiş Şarkıları' in row and str(row['Geçmiş Şarkıları']) != 'nan':
                songs = str(row['Geçmiş Şarkıları']).split(';')
                for song_name in songs:
                    s_name = song_name.strip()
                    if s_name:
                        # Şarkıyı bul veya oluştur
                        db_song = db.query(models.Song).filter(models.Song.title == s_name).first()
                        if not db_song:
                            db_song = models.Song(title=s_name, artist="Bilinmiyor", genre="Pop", theme="Genel")
                            db.add(db_song)
                            db.commit()
                            db.refresh(db_song)
                        
                        # Geçmişe işle
                        hist = models.ListeningHistory(user_id=db_user.id, song_id=db_song.id)
                        db.add(hist)
                        db.commit()

            basarili += 1
            if basarili % 10 == 0:
                print(f"✅ {basarili} kullanıcı tamamlandı...")

        except Exception as e:
            db.rollback() # Hata olursa veritabanını geri al
            hatali += 1
            print(f"❌ SATIR {index} HATASI: {e}")
            
            continue

    db.close()
    print("\n----------------SONUÇ RAPORU----------------")
    print(f"✅ Başarılı: {basarili}")
    print(f"❌ Hatalı:   {hatali}")
    print("--------------------------------------------")

if __name__ == "__main__":
    veri_yukle_baslat()
