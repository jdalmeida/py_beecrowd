"""
Atalho: roda o benchmark e em seguida gera tabelas/graficos.

Argumentos sao repassados para o benchmark. Para customizar o relatorio, use
diretamente `python relatorio.py --csv <caminho>`.
"""

import sys

import benchmark
import relatorio


if __name__ == "__main__":
    print(">> Etapa 1/2: benchmark")
    benchmark.main(sys.argv[1:])

    print("\n>> Etapa 2/2: relatorio (tabelas + graficos)")
    relatorio.main([])
