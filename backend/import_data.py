import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, schemas, crud, ai_service
import json
import os

# Veritabanı tablolarını oluştur
models.Base.metadata.create_all(bind=engine)

def import_csv_to_db():
    csv_file_path = "kullancı veri seti müzik öneri sistemi.csv"
    
    # 1. DOSYA KONTROLÜ
    if not os.path.exists(csv_file_path):
        print(f"❌ HATA: '{csv_file_path}' dosyası bulunamadı!")
        print(f"📂 Şu anki klasör: {os.getcwd()}")
        print("Lütfen dosyayı 'backend' klasörünün içine attığından emin ol.")
        return

    print("📊 Veri seti okunuyor...")
    try:
        # Encoding hatası olmaması için utf-8 ekliyoruz
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        # Sütun isimlerindeki boşlukları temizleyelim (Örn: " Email " -> "Email")
        df.columns = df.columns.str.strip()
        
        print("✅ Sütunlar bulundu:", df.columns.tolist())
        
    except Exception as e:
        print(f"❌ CSV okuma hatası: {e}")
        return

    db = SessionLocal()
    print(f"🚀 Toplam {len(df)} satır veri işlenecek...")

    success_count = 0
    error_count = 0
    
    for index, row in df.iterrows():
        try:
            # Verileri alırken hata olursa yakala
            email = str(row['Email']).strip()
            username = str(row['Nickname']).strip()
            password = str(row['Şifre']).strip()
            
            # NLP Verileri
            activity = str(row['Ne Yaparken Dinlediği'])
            genres = str(row['Şarkı Türü'])
            mood = str(row['Şarkı Duygusu'])

            # Kullanıcı Zaten Var mı?
            if crud.get_user_by_email(db, email=email):
                print(f"⚠️ Satır {index}: {email} zaten kayıtlı.")
                continue

            # 1. KULLANICI KAYDET
            user_in = schemas.UserCreate(username=username, email=email, password=password)
            created_user = crud.create_user(db=db, user=user_in)

            # 2. VEKTÖR HESAPLA
            combined_text = f"Aktivite: {activity}. Sevdiği Türler: {genres}. Ruh Hali: {mood}"
            vector_list = ai_service.get_mood_vector(combined_text)
            
            # 3. PROFİL KAYDET
            try: age_val = int(row['Yaş'])
            except: age_val = 18

            profile_in = schemas.ProfileCreate(
                age=age_val,
                location="İstanbul",
                hobbies=activity,
                favorite_genres=genres,
                mood_description=mood
            )

            crud.create_user_profile(
                db=db, 
                profile=profile_in, 
                user_id=created_user.id, 
                mood_vector_json=json.dumps(vector_list)
            )
            
            # 4. GEÇMİŞ ŞARKILARI KAYDET
            if 'Geçmiş Şarkıları' in row and str(row['Geçmiş Şarkıları']) != 'nan':
                songs = str(row['Geçmiş Şarkıları']).split(';')
                for song_name in songs:
                    s_name = song_name.strip()
                    if s_name:
                        # Şarkı var mı bak, yoksa ekle
                        db_song = db.query(models.Song).filter(models.Song.title == s_name).first()
                        if not db_song:
                            db_song = models.Song(title=s_name)
                            db.add(db_song)
                            db.commit()
                            db.refresh(db_song)
                        
                        # Geçmişe ekle
                        hist = models.ListeningHistory(user_id=created_user.id, song_id=db_song.id)
                        db.add(hist)
                        db.commit()

            success_count += 1
            if success_count % 10 == 0:
                print(f"✅ {success_count} kullanıcı işlendi...")

        except Exception as e:
            error_count += 1
            print(f"❌ SATIR {index} HATASI: {e}")
            continue

    db.close()
    print("\n----------------SONUÇ RAPORU----------------")
    print(f"✅ Başarılı: {success_count}")
    print(f"❌ Hatalı:   {error_count}")
    print("--------------------------------------------")

if __name__ == "__main__":
    import_csv_to_db()