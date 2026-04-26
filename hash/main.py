import numpy as np

# Reutilizando a função MurmurHash3 (32-bit) que discutimos
def murmur3_32(key, seed=0):
    c1, c2 = 0xcc9e2d51, 0x1b873593
    r1, r2 = 15, 13
    m, n = 5, 0xe6546b64
    data = bytearray(key.encode('utf-8'))
    length = len(data)
    n_blocks = length // 4
    h1 = seed
    for i in range(0, n_blocks * 4, 4):
        k1 = data[i] | (data[i+1] << 8) | (data[i+2] << 16) | (data[i+3] << 24)
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << r1) | (k1 >> (32 - r1))) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << r2) | (h1 >> (32 - r2))) & 0xFFFFFFFF
        h1 = (h1 * m + n) & 0xFFFFFFFF
    tail_index = n_blocks * 4
    k1 = 0
    remaining = length % 4
    if remaining >= 3: k1 ^= data[tail_index + 2] << 16
    if remaining >= 2: k1 ^= data[tail_index + 1] << 8
    if remaining >= 1: 
        k1 ^= data[tail_index]; k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << r1) | (k1 >> (32 - r1))) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF; h1 ^= k1
    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
    h1 ^= h1 >> 13
    h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
    h1 ^= h1 >> 16
    return h1

class TabelaHashSpam:
    def __init__(self, capacidade):
        self.capacidade = capacidade
        # Criamos uma lista de listas para o encadeamento
        self.tabela = [[] for _ in range(capacidade)]
    
    def adicionar(self, email):
        indice = murmur3_32(email) % self.capacidade
        if email not in self.tabela[indice]:
            self.tabela[indice].append(email)
            
    def verificar(self, email):
        indice = murmur3_32(email) % self.capacidade
        return email in self.tabela[indice]

# --- SCRIPT DE USO REAL ---

def gerar_emails_aleatorios(n):
    dominios = ["gmail.com", "outlook.com", "spam.net", "promocao.org", "teste.io"]
    # Gerar prefixos aleatórios usando numpy
    letras = np.array(list('abcdefghijklmnopqrstuvwxyz'))
    # Criar n prefixos de 8 letras cada
    prefixos_matriz = np.random.choice(letras, size=(n, 8))
    prefixos = ["".join(linha) for linha in prefixos_matriz]
    
    emails = [f"{p}@{np.random.choice(dominios)}" for p in prefixos]
    return np.array(emails)

# 1. Definir quantidade
N_EMAILS = 1000

# 2. Gerar base de dados de emails
base_dados = gerar_emails_aleatorios(N_EMAILS)

# 3. Criar a Tabela Hash (Blacklist de Spam)
# Recomendado: tamanho da tabela ser ~1.3x o número de itens para poucas colisões
blacklist = TabelaHashSpam(capacidade=int(N_EMAILS * 1.3))

# 4. "Treinar" colocando metade da base na blacklist
metade = N_EMAILS // 2
for i in range(metade):
    blacklist.adicionar(base_dados[i])

print(f"--- Tabela populada com {metade} emails de spam ---")

# 5. Simular Verificação
email_teste_1 = base_dados[0]        # Está na lista
email_teste_2 = "usuario_novo@bom.com" # Não está na lista

for email in [email_teste_1, email_teste_2]:
    resultado = "BLOQUEADO (Spam)" if blacklist.verificar(email) else "LIBERADO (Seguro)"
    print(f"Verificando {email}: {resultado}")
