import random
from dataclasses import dataclass


@dataclass
class Contador:
    """Acumula indicadores de uma execucao de ordenacao."""

    comparacoes: int = 0
    trocas: int = 0

    def cmp(self, a, b) -> int:
        """Compara dois valores e contabiliza. Retorna -1, 0 ou 1."""
        self.comparacoes += 1
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def menor(self, a, b) -> bool:
        self.comparacoes += 1
        return a < b

    def maior(self, a, b) -> bool:
        self.comparacoes += 1
        return a > b

    def trocar(self, vetor, i, j) -> None:
        """Swap entre duas posicoes. Conta 1 troca mesmo se i == j (chamada)."""
        if i != j:
            vetor[i], vetor[j] = vetor[j], vetor[i]
        self.trocas += 1


# --------------------------------------------------------------------------
# Insertion Sort  -- O(n^2) medio/pior, O(n) melhor (vetor ja ordenado)
# --------------------------------------------------------------------------
def insertion_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    for i in range(1, n):
        chave = vetor[i]
        j = i - 1
        deslocou = False
        # Desloca elementos maiores que a chave uma posicao a direita.
        while j >= 0:
            c.comparacoes += 1
            if vetor[j] <= chave:
                break
            vetor[j + 1] = vetor[j]
            c.trocas += 1
            j -= 1
            deslocou = True
        if deslocou:
            vetor[j + 1] = chave
    return vetor


# --------------------------------------------------------------------------
# Selection Sort  -- O(n^2) em todos os casos
# --------------------------------------------------------------------------
def selection_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    for i in range(n - 1):
        idx_min = i
        for j in range(i + 1, n):
            if c.menor(vetor[j], vetor[idx_min]):
                idx_min = j
        if idx_min != i:
            c.trocar(vetor, i, idx_min)
    return vetor


# --------------------------------------------------------------------------
# Shell Sort  -- gap sequence de Knuth (3*h + 1).
# Complexidade empirica ~ O(n^1.3); pior conhecido O(n^(3/2)).
# --------------------------------------------------------------------------
def shell_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    if n < 2:
        return vetor

    # Gera sequencia de Knuth: 1, 4, 13, 40, 121, ... menor que n.
    gap = 1
    while gap < n // 3:
        gap = gap * 3 + 1

    while gap >= 1:
        for i in range(gap, n):
            chave = vetor[i]
            j = i
            while j >= gap:
                c.comparacoes += 1
                if vetor[j - gap] <= chave:
                    break
                vetor[j] = vetor[j - gap]
                c.trocas += 1
                j -= gap
            vetor[j] = chave
        gap //= 3
    return vetor


# --------------------------------------------------------------------------
# Merge Sort  -- O(n log n) em todos os casos. Implementacao iterativa
# (bottom-up) para evitar estouro de pilha em massas de dados grandes.
# --------------------------------------------------------------------------
def merge_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    if n < 2:
        return vetor

    aux = [0] * n
    largura = 1
    while largura < n:
        for inicio in range(0, n, 2 * largura):
            meio = min(inicio + largura, n)
            fim = min(inicio + 2 * largura, n)
            _merge(vetor, aux, inicio, meio, fim, c)
        largura *= 2
    return vetor


def _merge(vetor, aux, inicio, meio, fim, c: Contador) -> None:
    # Copia a metade esquerda para o auxiliar; metade direita permanece in-place.
    for k in range(inicio, meio):
        aux[k] = vetor[k]

    i, j, k = inicio, meio, inicio
    while i < meio and j < fim:
        c.comparacoes += 1
        if aux[i] <= vetor[j]:
            vetor[k] = aux[i]
            i += 1
        else:
            vetor[k] = vetor[j]
            j += 1
        c.trocas += 1
        k += 1
    # Drena resto da metade esquerda (a direita ja esta no lugar).
    while i < meio:
        vetor[k] = aux[i]
        c.trocas += 1
        i += 1
        k += 1


# --------------------------------------------------------------------------
# Quick Sort  -- particao 3-way (Dutch National Flag) com pivo mediana-de-tres.
# Iterativo na particao maior para limitar profundidade de recursao a O(log n).
# Medio O(n log n); pior O(n^2) raro com mediana-de-tres + 3-way em duplicatas.
# --------------------------------------------------------------------------
def quick_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    if n < 2:
        return vetor
    _quick(vetor, 0, n - 1, c)
    return vetor


def _mediana_de_tres(vetor, lo, hi, c: Contador) -> None:
    """Coloca a mediana de tres posicoes amostradas aleatoriamente em vetor[lo]."""
    if hi - lo >= 2:
        a = random.randint(lo, hi)
        b = random.randint(lo, hi)
        d = random.randint(lo, hi)
    else:
        a, b, d = lo, lo, hi

    # Ordena os tres indices pelos seus valores via 3 comparacoes contadas.
    if c.menor(vetor[b], vetor[a]):
        a, b = b, a
    if c.menor(vetor[d], vetor[a]):
        a, d = d, a
    if c.menor(vetor[d], vetor[b]):
        b, d = d, b
    # Agora vetor[a] <= vetor[b] <= vetor[d]; b indica a mediana.
    c.trocar(vetor, lo, b)


def _quick(vetor, lo, hi, c: Contador) -> None:
    while lo < hi:
        if hi - lo < 16:
            # Particoes pequenas: insertion sort costuma ser mais barato.
            for i in range(lo + 1, hi + 1):
                chave = vetor[i]
                j = i - 1
                while j >= lo:
                    c.comparacoes += 1
                    if vetor[j] <= chave:
                        break
                    vetor[j + 1] = vetor[j]
                    c.trocas += 1
                    j -= 1
                vetor[j + 1] = chave
            return

        _mediana_de_tres(vetor, lo, hi, c)
        pivo = vetor[lo]
        # Particao 3-way: [lo..lt-1] < pivo, [lt..gt] == pivo, [gt+1..hi] > pivo
        lt, i, gt = lo, lo + 1, hi
        while i <= gt:
            cmp = c.cmp(vetor[i], pivo)
            if cmp < 0:
                c.trocar(vetor, lt, i)
                lt += 1
                i += 1
            elif cmp > 0:
                c.trocar(vetor, i, gt)
                gt -= 1
            else:
                i += 1

        # Recursao na particao menor; itera na maior (cauda).
        if lt - lo < hi - gt:
            _quick(vetor, lo, lt - 1, c)
            lo = gt + 1
        else:
            _quick(vetor, gt + 1, hi, c)
            hi = lt - 1


# --------------------------------------------------------------------------
# Radix Sort  -- LSD para inteiros nao-negativos, base 10. O(d*(n+b)).
# Para inteiros com sinal, separa negativos e positivos e concatena.
# --------------------------------------------------------------------------
def radix_sort(vetor: list, c: Contador) -> list:
    n = len(vetor)
    if n < 2:
        return vetor

    # Separa sinais para suportar negativos sem custo de offset.
    negativos = [-x for x in vetor if x < 0]
    positivos = [x for x in vetor if x >= 0]

    if positivos:
        _radix_lsd(positivos, c)
    if negativos:
        _radix_lsd(negativos, c)
        negativos = [-x for x in reversed(negativos)]

    # Reescreve in-place mantendo identidade da lista para o runner.
    vetor[:] = negativos + positivos
    # Cada elemento foi movido pelo menos uma vez para reescrever in-place.
    c.trocas += n
    return vetor


def _radix_lsd(vetor: list, c: Contador) -> None:
    if not vetor:
        return
    maximo = max(vetor)
    # max() faz n-1 comparacoes internas.
    c.comparacoes += len(vetor) - 1

    exp = 1
    while maximo // exp > 0:
        _counting_sort_por_digito(vetor, exp, c)
        exp *= 10


def _counting_sort_por_digito(vetor: list, exp: int, c: Contador) -> None:
    n = len(vetor)
    saida = [0] * n
    contagem = [0] * 10

    for x in vetor:
        digito = (x // exp) % 10
        contagem[digito] += 1

    for i in range(1, 10):
        contagem[i] += contagem[i - 1]

    # Iteracao reversa preserva estabilidade.
    for i in range(n - 1, -1, -1):
        digito = (vetor[i] // exp) % 10
        contagem[digito] -= 1
        saida[contagem[digito]] = vetor[i]
        c.trocas += 1

    for i in range(n):
        vetor[i] = saida[i]
        c.trocas += 1


# Mapa publico utilizado pelo benchmark.
ALGORITMOS = {
    "Insertion Sort": insertion_sort,
    "Selection Sort": selection_sort,
    "Shell Sort": shell_sort,
    "Merge Sort": merge_sort,
    "Quick Sort": quick_sort,
    "Radix Sort": radix_sort,
}

# Classificacao Big-O para o relatorio.
BIG_O = {
    "Insertion Sort": {
        "melhor": "O(n)",
        "medio": "O(n^2)",
        "pior": "O(n^2)",
        "memoria": "O(1)",
    },
    "Selection Sort": {
        "melhor": "O(n^2)",
        "medio": "O(n^2)",
        "pior": "O(n^2)",
        "memoria": "O(1)",
    },
    "Shell Sort": {
        "melhor": "O(n log n)",
        "medio": "O(n^1.3)",
        "pior": "O(n^1.5)",
        "memoria": "O(1)",
    },
    "Merge Sort": {
        "melhor": "O(n log n)",
        "medio": "O(n log n)",
        "pior": "O(n log n)",
        "memoria": "O(n)",
    },
    "Quick Sort": {
        "melhor": "O(n log n)",
        "medio": "O(n log n)",
        "pior": "O(n^2)",
        "memoria": "O(log n)",
    },
    "Radix Sort": {
        "melhor": "O(d(n+b))",
        "medio": "O(d(n+b))",
        "pior": "O(d(n+b))",
        "memoria": "O(n+b)",
    },
}
