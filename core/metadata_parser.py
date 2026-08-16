import re
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import piexif

class MetadataParser:
    """Lê metadados customizados do campo UserComment do EXIF."""

    @staticmethod
    def extract_custom_metadata(image_path):
        """Extrai metadados do campo UserComment do EXIF."""
        path = Path(image_path)
        if not path.exists():
            return None

        try:
            exif_dict = piexif.load(str(path))
            user_comment = None
            
            if "Exif" in exif_dict:
                exif_data = exif_dict["Exif"]
                if piexif.ExifIFD.UserComment in exif_data:
                    user_comment_bytes = exif_data[piexif.ExifIFD.UserComment]
                    user_comment = MetadataParser._decode_user_comment(user_comment_bytes)
            
            if user_comment is None:
                user_comment = MetadataParser._extract_with_pillow(path)
            
            if user_comment is None:
                user_comment = MetadataParser._extract_from_binary(path)
            
            if not user_comment:
                return None
            
            return MetadataParser._parse_user_comment(user_comment)
            
        except:
            return MetadataParser._extract_from_binary(path)

    @staticmethod
    def _decode_user_comment(data):
        """Decodifica o UserComment do EXIF."""
        if not data:
            return None
        
        try:
            if isinstance(data, bytes):
                # Verificar prefixo de codificação
                if data[:8] == b'UNICODE\x00':
                    content = data[8:]
                    return content.decode('utf-16', errors='ignore').rstrip('\x00')
                elif data[:8] == b'ASCII\x00\x00\x00':
                    content = data[8:]
                    try:
                        return content.decode('utf-8').rstrip('\x00')
                    except:
                        try:
                            return content.decode('latin-1').rstrip('\x00')
                        except:
                            return content.decode('ascii', errors='ignore').rstrip('\x00')
                else:
                    # Tentar múltiplas codificações
                    try:
                        return data.decode('utf-8').rstrip('\x00')
                    except:
                        pass
                    try:
                        decoded = data.decode('latin-1').rstrip('\x00')
                        if any(c.isalpha() for c in decoded):
                            return decoded
                    except:
                        pass
                    return data.decode('ascii', errors='ignore').rstrip('\x00')
            
            elif isinstance(data, str):
                return data.rstrip('\x00')
        except:
            pass
        
        return None

    @staticmethod
    def _extract_with_pillow(path):
        """Extrai UserComment usando Pillow."""
        try:
            with Image.open(path) as img:
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name == 'UserComment':
                            return MetadataParser._decode_user_comment(value)
        except:
            pass
        return None

    @staticmethod
    def _extract_from_binary(path):
        """Fallback: leitura binária."""
        try:
            with open(path, "rb") as f:
                data = f.read(200000).replace(b"\x00", b"")
            
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = data.decode(encoding, errors='ignore')
                    pattern = re.compile(r'([^|<]+)\|([^|<]+)\|([^|<]+)\|([^|<]+)\|([^|<]+)\|([^|<]+)\|([^|<]+)')
                    match = pattern.search(text)
                    if match:
                        return '|'.join(match.groups())
                except:
                    continue
        except:
            pass
        return None

    @staticmethod
    def _parse_user_comment(comment_text):
        """Parseia o texto do UserComment."""
        if not comment_text:
            return None
        
        comment_text = comment_text.strip()
        parts = comment_text.split('|')
        
        if len(parts) < 6:
            return None
        
        return {
            "obra": parts[0].strip() if len(parts) > 0 else "",
            "servico": parts[1].strip() if len(parts) > 1 else "",
            "estaca": parts[2].strip() if len(parts) > 2 else "",
            "lado": parts[3].strip() if len(parts) > 3 else "",
            "utm": parts[4].strip() if len(parts) > 4 else "",
            "data": parts[5].strip() if len(parts) > 5 else "",
            "hora": parts[6].strip() if len(parts) > 6 else "",
            "extra": '|'.join(parts[7:]) if len(parts) > 7 else ""
        }

    @staticmethod
    def corrigir_caracteres_especiais(texto):
        """Corrige caracteres especiais em português."""
        if not texto:
            return texto
        
        texto_upper = texto.upper()
        
        correcoes = {
            'REMOO DE RVORES': 'REMOÇÃO DE ÁRVORES',
            'REMOO DE ARVORES': 'REMOÇÃO DE ÁRVORES',
            'REMOCAO DE ARVORES': 'REMOÇÃO DE ÁRVORES',
            'REMOCAO DE RVORES': 'REMOÇÃO DE ÁRVORES',
            'REMOO': 'REMOÇÃO',
            'RVORES': 'ÁRVORES',
            'REFORCO': 'REFORÇO',
            'REMOCO': 'REMOÇO',
            'ROCA': 'ROÇA',
            'ROCAGEM': 'ROÇAGEM',
            'IMPREGNACAO': 'IMPREGNAÇÃO',
            'APLICACAO': 'APLICAÇÃO',
            'PINTURA DE LIGACAO': 'PINTURA DE LIGAÇÃO',
            'CORRECAO': 'CORREÇÃO',
            'REGULARIZACAO': 'REGULARIZAÇÃO',
            'RECOMPOSICAO': 'RECOMPOSIÇÃO',
            'REMOCAO': 'REMOÇÃO',
            'SINALIZACAO': 'SINALIZAÇÃO',
            'EXECUCAO': 'EXECUÇÃO',
            'IMPLANTACAO': 'IMPLANTAÇÃO',
            'DOMINIO': 'DOMÍNIO',
            'TEMPORARIA': 'TEMPORÁRIA',
            'ARVORES': 'ÁRVORES',
            'PONTILHAO': 'PONTILHÃO',
            'EROSAO': 'EROSÃO',
            'LIGACAO': 'LIGAÇÃO',
            'PRIMARIO': 'PRIMÁRIO',
            'SERVICO': 'SERVIÇO',
            'CAMADA DE REFORCO': 'CAMADA DE REFORÇO',
            'EXECUCAO DE BUEIRO': 'EXECUÇÃO DE BUEIRO',
            'EXECUCAO DE PONTILHAO': 'EXECUÇÃO DE PONTILHÃO',
            'FAIXA DE DOMINIO': 'FAIXA DE DOMÍNIO',
            'IMPLANTACAO DE PLACAS': 'IMPLANTAÇÃO DE PLACAS',
            'LANCAMENTO DE BGS': 'LANÇAMENTO DE BGS',
            'PINTURA DE LIGACAO': 'PINTURA DE LIGAÇÃO',
            'RECOMPOSICAO MECANIZADA DE ATERRO': 'RECOMPOSIÇÃO MECANIZADA DE ATERRO',
            'REGULARIZACAO DE SUBLEITO': 'REGULARIZAÇÃO DE SUBLEITO',
            'REMOCAO DE ARVORES': 'REMOÇÃO DE ÁRVORES',
            'REVESTIMENTO PRIMARIO 01': 'REVESTIMENTO PRIMÁRIO 01',
            'REVESTIMENTO PRIMARIO 02': 'REVESTIMENTO PRIMÁRIO 02',
            'SINALIZACAO TEMPORARIA': 'SINALIZAÇÃO TEMPORÁRIA',
            'SINALIZACAO VERTICAL': 'SINALIZAÇÃO VERTICAL',
        }
        
        texto_corrigido = texto_upper
        
        # Substituições mais longas primeiro
        for errado in sorted(correcoes.keys(), key=len, reverse=True):
            if errado in texto_corrigido:
                texto_corrigido = texto_corrigido.replace(errado, correcoes[errado])
        
        return texto_corrigido

    @staticmethod
    def limpar_texto(texto):
        """Limpa e normaliza uma string."""
        if not texto:
            return ""
        
        texto = texto.replace('\x00', '')
        texto = re.sub(r'\s+', ' ', texto).strip()
        texto = texto.upper()
        texto = MetadataParser.corrigir_caracteres_especiais(texto)
        
        return texto