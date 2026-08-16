import re

class EstacaAdjuster:
    """Ajusta o valor da estaca somando ou subtraindo um valor."""

    @staticmethod
    def parse_estaca(estaca_str):
        """Converte string de estaca para valor numérico em metros."""
        if not estaca_str:
            return 0
        
        estaca_str = str(estaca_str).strip().upper()
        
        try:
            # Se for apenas número
            if re.match(r'^\d+$', estaca_str):
                return int(estaca_str)
            
            # Formato KM+METROS (ex: 3+200)
            match = re.match(r'^(\d+)\+(\d+)$', estaca_str)
            if match:
                km = int(match.group(1))
                metros = int(match.group(2))
                return km * 1000 + metros
            
            # Formato com vírgula (ex: 3+200,50)
            match = re.match(r'^(\d+)\+(\d+)[,.](\d+)$', estaca_str)
            if match:
                km = int(match.group(1))
                metros = int(match.group(2))
                centimetros = int(match.group(3))
                return km * 1000 + metros + centimetros / 100
            
            # Extrair apenas números
            numeros = re.findall(r'\d+', estaca_str)
            if numeros:
                return int(numeros[0])
        except:
            pass
        
        return 0

    @staticmethod
    def format_estaca(valor_metros):
        """Converte valor numérico para formato de estaca."""
        if valor_metros < 0:
            valor_metros = 0
        
        km = int(valor_metros // 1000)
        metros = int(valor_metros % 1000)
        
        return f"{km}+{metros:03d}"

    @staticmethod
    def adjust_estaca(estaca_str, adjustment):
        """Ajusta a estaca somando ou subtraindo um valor."""
        valor_atual = EstacaAdjuster.parse_estaca(estaca_str)
        novo_valor = valor_atual + adjustment
        return EstacaAdjuster.format_estaca(novo_valor)

    @staticmethod
    def apply_adjustment_to_text(estaca_str, adjustment):
        """Aplica o ajuste e retorna a string da estaca."""
        if adjustment == 0:
            return estaca_str
        return EstacaAdjuster.adjust_estaca(estaca_str, adjustment)