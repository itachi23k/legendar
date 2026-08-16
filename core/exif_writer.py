import piexif
from PIL import Image
from pathlib import Path

class ExifWriter:
    """Grava metadados EXIF UserComment nas imagens processadas."""

    @staticmethod
    def copy_exif_from_source(source_path, dest_path):
        """Copia todo o EXIF do arquivo fonte para o destino."""
        try:
            exif_dict = piexif.load(source_path)
            if not exif_dict:
                return False
            
            exif_bytes = piexif.dump(exif_dict)
            img = Image.open(dest_path)
            
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            img.save(dest_path, "jpeg", exif=exif_bytes, quality=95)
            return True
        except:
            return False

    @staticmethod
    def write_user_comment(image_path, obra, servico, estaca, lado, utm, data, hora=""):
        """Grava o UserComment no formato padrão."""
        try:
            user_comment_text = f"{obra}|{servico}|{estaca}|{lado}|{utm}|{data}|{hora}"
            user_comment_bytes = b'UNICODE\x00' + user_comment_text.encode('utf-16')
            
            try:
                exif_dict = piexif.load(image_path)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}
            
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment_bytes
            exif_bytes = piexif.dump(exif_dict)
            
            img = Image.open(image_path)
            
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            img.save(image_path, "jpeg", exif=exif_bytes, quality=95)
            return True
        except:
            return False

    @staticmethod
    def update_user_comment_from_metadata(image_path, metadata_dict):
        """Atualiza o UserComment da imagem."""
        return ExifWriter.write_user_comment(
            image_path,
            metadata_dict.get('obra', ''),
            metadata_dict.get('servico', ''),
            metadata_dict.get('estaca', ''),
            metadata_dict.get('lado', ''),
            metadata_dict.get('utm', ''),
            metadata_dict.get('data', ''),
            metadata_dict.get('hora', '')
        )

    @staticmethod
    def preserve_original_exif(source_path, dest_path):
        """Copia o EXIF original para o arquivo de saída."""
        if ExifWriter.copy_exif_from_source(source_path, dest_path):
            return True
        
        try:
            from core.metadata_parser import MetadataParser
            meta = MetadataParser.extract_custom_metadata(source_path)
            if meta:
                return ExifWriter.update_user_comment_from_metadata(dest_path, meta)
        except:
            pass
        
        return False