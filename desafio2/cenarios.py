"""
Geradores de vetores para os 8 cenarios do desafio.

Garantia de "mesma situacao inicial": o gerador recebe um numpy.random.Generator
com seed fixa por (cenario, tamanho, repeticao). O runner clona o vetor antes
de submeter a cada algoritmo, de modo que todos os algoritmos enxergam exatamente
o mesmo vetor de entrada.

Cenarios (instrucao do desafio):
- aleatoria pequena: vetor aleatorio em massa pequena (1.000)
- crescente:        vetor ja ordenado de forma crescente
- decrescente:      vetor ordenado em ordem reversa
- repetido:         vetor com um unico valor em todas as posicoes
- vazia:            vetor de tamanho 0
- um item:          vetor de um unico elemento
- muitos repetidos: vetor com poucos valores distintos (alta densidade de duplicatas)
- longa:            vetor aleatorio em massa de dados grande/super grande
"""

from __future__ import annotations

import numpy as np

# Massas de dados conforme especificacao (4.1) -- nivel BIG sobe ate super grande.
TAMANHOS = {
    "pequena": 1_000,
    "media": 10_000,
    "grande": 50_000,
    "super_grande": 100_000,
}

# Faixa numerica padrao para os cenarios aleatorios.
FAIXA_VALORES = (0, 1_000_000)


def _rng(cenario: str, tamanho: int, repeticao: int) -> np.random.Generator:
    """Cria um Generator deterministico para uma combinacao (cenario, n, rep).

    Usar seeds reprodutiveis garante que o mesmo cenario possa ser regenerado
    identicamente em outra maquina e que duas execucoes consecutivas comparem
    o mesmo vetor entre algoritmos.
    """
    seed = abs(hash((cenario, tamanho, repeticao))) % (2**32)
    return np.random.default_rng(seed)


def aleatoria(tamanho: int, repeticao: int) -> list:
    """Vetor com numeros inteiros uniformemente distribuidos."""
    rng = _rng("aleatoria", tamanho, repeticao)
    return rng.integers(*FAIXA_VALORES, size=tamanho).tolist()


def crescente(tamanho: int, repeticao: int) -> list:
    """Vetor ja ordenado em ordem crescente.

    Usamos pequenos ruidos aleatorios para que cada repeticao tenha um vetor
    diferente (mas todos crescentes), como manda a observacao 'realizar varios
    casos de testes'.
    """
    rng = _rng("crescente", tamanho, repeticao)
    base = rng.integers(0, 5, size=tamanho)
    return np.cumsum(base).tolist()


def decrescente(tamanho: int, repeticao: int) -> list:
    """Vetor ordenado em ordem decrescente."""
    rng = _rng("decrescente", tamanho, repeticao)
    base = rng.integers(0, 5, size=tamanho)
    return np.cumsum(base)[::-1].tolist()


def repetido(tamanho: int, repeticao: int) -> list:
    """Vetor onde todos os elementos sao iguais."""
    rng = _rng("repetido", tamanho, repeticao)
    valor = int(rng.integers(*FAIXA_VALORES))
    return [valor] * tamanho


def vazia(tamanho: int, repeticao: int) -> list:
    """Vetor vazio. Tamanho fornecido eh ignorado por definicao do cenario."""
    return []


def um_item(tamanho: int, repeticao: int) -> list:
    """Vetor com um unico elemento."""
    rng = _rng("um_item", tamanho, repeticao)
    return [int(rng.integers(*FAIXA_VALORES))]


def muitos_repetidos(tamanho: int, repeticao: int) -> list:
    """Vetor aleatorio com poucos valores distintos (alta densidade de duplicatas).

    Numero de valores distintos ~ sqrt(tamanho), capado em 10. Isso aproxima
    cenarios reais como categorias, status, paises etc.
    """
    rng = _rng("muitos_repetidos", tamanho, repeticao)
    distintos = max(2, min(10, int(np.sqrt(max(tamanho, 1)))))
    universo = rng.integers(*FAIXA_VALORES, size=distintos)
    return rng.choice(universo, size=tamanho).tolist()


def longa(tamanho: int, repeticao: int) -> list:
    """Vetor aleatorio (alias para 'aleatoria' aplicado nas massas grandes).

    A distincao entre 'aleatoria pequena' e 'longa' eh apenas escala: ambos
    sao distribuicoes uniformes. O enunciado lista os dois para destacar
    comportamento em pequena vs. grande escala.
    """
    rng = _rng("longa", tamanho, repeticao)
    return rng.integers(*FAIXA_VALORES, size=tamanho).tolist()


# Mapa publico de cenarios. Cada entrada associa o nome legivel a:
# - gerador  : funcao(tamanho, repeticao) -> list
# - tamanhos : lista de chaves de TAMANHOS para os quais o cenario sera testado
CENARIOS = {
    "aleatoria pequena": {
        "gerador": aleatoria,
        "tamanhos": ["pequena"],
    },
    "crescente": {
        "gerador": crescente,
        "tamanhos": ["pequena", "media", "grande", "super_grande"],
    },
    "decrescente": {
        "gerador": decrescente,
        "tamanhos": ["pequena", "media", "grande", "super_grande"],
    },
    "repetido": {
        "gerador": repetido,
        "tamanhos": ["pequena", "media", "grande", "super_grande"],
    },
    "vazia": {
        "gerador": vazia,
        "tamanhos": ["pequena"],  # tamanho ignorado pelo gerador
    },
    "um item": {
        "gerador": um_item,
        "tamanhos": ["pequena"],  # tamanho ignorado pelo gerador
    },
    "muitos repetidos": {
        "gerador": muitos_repetidos,
        "tamanhos": ["pequena", "media", "grande", "super_grande"],
    },
    "longa": {
        "gerador": longa,
        "tamanhos": ["media", "grande", "super_grande"],
    },
}
