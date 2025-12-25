# playlist_service.py (Yeni Dosya)
from sqlalchemy.orm import Session
from sqlalchemy import desc
import models, schemas
from fastapi import HTTPException

class PlaylistManager:
    """
    Playlist ve Favori işlemlerini yöneten sınıf.
    Limit kontrolleri ve iş mantığı burada yer alır.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def create_playlist(self, user_id: int, name: str, is_favorite: bool = False):
        # KURAL 1: Max 40 Playlist Kontrolü (Favori listesi hariç ise)
        if not is_favorite:
            count = self.db.query(models.Playlist).filter(
                models.Playlist.user_id == user_id, 
                models.Playlist.is_favorite == False
            ).count()
            
            if count >= 40:
                raise HTTPException(status_code=400, detail="Maksimum playlist sınırına (40) ulaştınız.")

        new_playlist = models.Playlist(name=name, user_id=user_id, is_favorite=is_favorite)
        self.db.add(new_playlist)
        self.db.commit()
        self.db.refresh(new_playlist)
        return new_playlist

    def get_user_playlists(self, user_id: int):
        return self.db.query(models.Playlist).filter(models.Playlist.user_id == user_id).all()

    def get_favorites_playlist(self, user_id: int):
        # Kullanıcının favori listesini bul
        fav_list = self.db.query(models.Playlist).filter(
            models.Playlist.user_id == user_id,
            models.Playlist.is_favorite == True
        ).first()
        
        # Eğer yoksa (eski kullanıcılar için) otomatik oluştur
        if not fav_list:
            fav_list = self.create_playlist(user_id, "Favorilenler", is_favorite=True)
        
        return fav_list

    def add_song_to_playlist(self, playlist_id: int, song_id: int):
        playlist = self.db.query(models.Playlist).filter(models.Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist bulunamadı.")

        # KURAL 2: Max 500 Şarkı Kontrolü
        song_count = self.db.query(models.PlaylistItem).filter(models.PlaylistItem.playlist_id == playlist_id).count()
        if song_count >= 500:
            raise HTTPException(status_code=400, detail="Bu playliste en fazla 500 şarkı eklenebilir.")

        # Şarkı zaten var mı?
        exists = self.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.playlist_id == playlist_id,
            models.PlaylistItem.song_id == song_id
        ).first()

        if exists:
            return exists # Zaten varsa işlem yapma veya hata döndür

        new_item = models.PlaylistItem(playlist_id=playlist_id, song_id=song_id)
        self.db.add(new_item)
        self.db.commit()
        return new_item

    def remove_song_from_playlist(self, playlist_id: int, song_id: int):
        item = self.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.playlist_id == playlist_id,
            models.PlaylistItem.song_id == song_id
        ).first()
        
        if item:
            self.db.delete(item)
            self.db.commit()
            return {"message": "Şarkı silindi"}
        raise HTTPException(status_code=404, detail="Şarkı bu listede bulunamadı.")

    def toggle_favorite(self, user_id: int, song_id: int):
        """
        Favori butonuna basıldığında çalışır.
        Şarkı favorilerde yoksa ekler (En üste), varsa çıkarır.
        """
        fav_playlist = self.get_favorites_playlist(user_id)
        
        # Kontrol et: Ekli mi?
        existing_item = self.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.playlist_id == fav_playlist.id,
            models.PlaylistItem.song_id == song_id
        ).first()

        if existing_item:
            # Varsa çıkar
            self.db.delete(existing_item)
            self.db.commit()
            return {"status": "removed", "message": "Favorilerden çıkarıldı"}
        else:
            # Yoksa ekle (Limit kontrolünü add_song_to_playlist içinde zaten yapıyor)
            self.add_song_to_playlist(fav_playlist.id, song_id)
            return {"status": "added", "message": "Favorilere eklendi"}