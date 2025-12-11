from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
import models

def get_similar_users(db: Session, current_user_id: int, top_k: int = 3):
    """
    Verilen kullanıcıya (current_user_id) en çok benzeyen diğer kullanıcıları bulur.
    Mantık: Cosine Similarity (Vektör Benzerliği)
    """
    
    # 1. Şu anki kullanıcının profilini bul
    current_profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user_id).first()
    
    # Profil veya vektör yoksa boş dön
    if not current_profile or not current_profile.mood_vector:
        return []
    
    # JSON String olan vektörü NumPy Array'e çevir
    # Örn: "[0.1, 0.2]" -> np.array([[0.1, 0.2]])
    try:
        current_vector = np.array(json.loads(current_profile.mood_vector)).reshape(1, -1)
    except:
        return [] # Vektör bozuksa boş dön

    # 2. Veritabanındaki DİĞER kullanıcıları çek (Kendisi hariç)
    other_profiles = db.query(models.UserProfile).filter(models.UserProfile.user_id != current_user_id).all()
    
    similarities = []

    for profile in other_profiles:
        if profile.mood_vector:
            try:
                # Diğer kullanıcının vektörünü hazırla
                target_vector = np.array(json.loads(profile.mood_vector)).reshape(1, -1)
                
                # 3. Benzerlik Skoru Hesapla (0 ile 1 arası)
                score = cosine_similarity(current_vector, target_vector)[0][0]
                
                similarities.append({
                    "user_id": profile.user_id,
                    "score": float(score), 
                    "username": profile.owner.username, # İlişkili tablodan ismini al
                    "match_reason": f"Benzerlik Oranı: %{int(score*100)}"
                })
            except:
                continue
    
    # 4. Sıralama Yap: Skoru en yüksek olan en üstte olsun
    similarities.sort(key=lambda x: x["score"], reverse=True)
    
    # 5. Sadece ilk 'top_k' (örn: 3) kişiyi döndür
    return similarities[:top_k]