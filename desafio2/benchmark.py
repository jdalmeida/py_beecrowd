"""
Runner do desafio comparativo de algoritmos de ordenacao.

Para cada combinacao (cenario, tamanho, repeticao):
- Gera UM unico vetor (sementes deterministicas em cenarios.py).
- Esse vetor eh COPIADO antes de ser entregue a cada algoritmo, garantindo
  que todos os algoritmos enxerguem o MESMO vetor de entrada (requisito 4.1).
- Cada execucao eh medida com time.perf_counter() (relogio monotonico de
  alta resolucao do SO), com gc desabilitado durante o trecho cronometrado
  para evitar pausas espurias.
- Cada execucao tem um time-budget (timeout). Algoritmos O(n^2) em massas
  super grandes podem ser cortados.

Saida: resultados/resultados.csv com uma linha por execucao.
"""

from __future__ import annotations

import argparse
import csv
import gc
import signal
import time
from contextlib import contextmanager
from pathlib import Path

from algoritmos import ALGORITMOS, Contador
from cenarios import CENARIOS, TAMANHOS

DIR_RESULTADOS = Path(__file__).parent / "resultados"
ARQUIVO_CSV_PADRAO = DIR_RESULTADOS / "resultados.csv"

CABECALHO = [
    "cenario", "tamanho_label", "n", "algoritmo", "repeticao",
    "tempo_s", "comparacoes", "trocas", "ordenado", "status",
]


class Timeout(Exception):
    """Sinaliza que o orcamento de tempo da execucao foi excedido."""


@contextmanager
def limite_tempo(segundos: float):
    """Aborta o bloco se exceder `segundos`. Usa SIGALRM (Unix-only)."""
    if segundos is None or segundos <= 0:
        yield
        return

    def handler(_signum, _frame):
        raise Timeout()

    anterior = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, segundos)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, anterior)


def _esta_ordenado(v: list) -> bool:
    """Verifica que o algoritmo de fato ordenou o vetor (validacao do resultado)."""
    return all(v[i] <= v[i + 1] for i in range(len(v) - 1))


def executar_uma(algoritmo, vetor, timeout):
    """Executa o algoritmo em uma copia independente do vetor.

    Retorna (tempo, comparacoes, trocas, ordenado, status).
    """
    # list() faz copia rasa - suficiente porque o conteudo eh int (imutavel).
    copia = list(vetor)
    contador = Contador()

    gc_estava_ativo = gc.isenabled()
    gc.disable()
    inicio = time.perf_counter()
    try:
        with limite_tempo(timeout):
            algoritmo(copia, contador)
        tempo = time.perf_counter() - inicio
        ordenado = _esta_ordenado(copia)
        status = "ok" if ordenado else "ERRO_NAO_ORDENOU"
    except Timeout:
        tempo = time.perf_counter() - inicio
        ordenado = False
        status = "TIMEOUT"
    finally:
        if gc_estava_ativo:
            gc.enable()

    return tempo, contador.comparacoes, contador.trocas, ordenado, status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--reps", type=int, default=3,
                        help="Repeticoes por combinacao (minimo 3 conforme regra)")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="Tempo maximo por execucao em segundos")
    parser.add_argument("--max-tamanho", choices=list(TAMANHOS.keys()),
                        default=None,
                        help="Limita o maior tamanho rodado")
    parser.add_argument("--min-tamanho", choices=list(TAMANHOS.keys()),
                        default=None,
                        help="Limita o menor tamanho rodado")
    parser.add_argument("--algoritmos", nargs="*", default=None,
                        help="Subconjunto de algoritmos por nome")
    parser.add_argument("--cenarios", nargs="*", default=None,
                        help="Subconjunto de cenarios por nome")
    parser.add_argument("--csv", default=str(ARQUIVO_CSV_PADRAO),
                        help="Arquivo CSV de saida")
    parser.add_argument("--append", action="store_true",
                        help="Anexa ao CSV existente em vez de sobrescrever")
    args = parser.parse_args(argv)

    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)

    algos = ALGORITMOS
    if args.algoritmos:
        algos = {k: v for k, v in ALGORITMOS.items() if k in args.algoritmos}
        ausentes = set(args.algoritmos) - set(algos)
        if ausentes:
            parser.error(f"Algoritmos desconhecidos: {sorted(ausentes)}")

    cenarios_alvo = CENARIOS
    if args.cenarios:
        cenarios_alvo = {k: v for k, v in CENARIOS.items() if k in args.cenarios}
        ausentes = set(args.cenarios) - set(cenarios_alvo)
        if ausentes:
            parser.error(f"Cenarios desconhecidos: {sorted(ausentes)}")

    ordem_tamanhos = list(TAMANHOS.keys())
    limite_max = (
        ordem_tamanhos.index(args.max_tamanho)
        if args.max_tamanho else len(ordem_tamanhos) - 1
    )
    limite_min = (
        ordem_tamanhos.index(args.min_tamanho) if args.min_tamanho else 0
    )

    def tamanho_permitido(tam: str) -> bool:
        idx = ordem_tamanhos.index(tam)
        return limite_min <= idx <= limite_max

    # Pre-conta o numero total de execucoes para a barra de progresso textual.
    total_combos = 0
    for info in cenarios_alvo.values():
        for tam in info["tamanhos"]:
            if tamanho_permitido(tam):
                total_combos += len(algos) * args.reps

    print(
        f"Total de execucoes: {total_combos} | "
        f"timeout/exec: {args.timeout:.0f}s | reps: {args.reps}"
    )

    feitos = 0
    modo = "a" if args.append and Path(args.csv).exists() else "w"
    with open(args.csv, modo, newline="", encoding="utf-8") as arq:
        writer = csv.writer(arq)
        if modo == "w":
            writer.writerow(CABECALHO)

        for nome_cenario, info in cenarios_alvo.items():
            for tam in info["tamanhos"]:
                if not tamanho_permitido(tam):
                    continue
                n_logico = TAMANHOS[tam]
                for rep in range(1, args.reps + 1):
                    # Gera UM vetor por (cenario, tamanho, rep). Os algoritmos
                    # recebem copias dele para preservar a "mesma situacao inicial".
                    vetor = info["gerador"](n_logico, rep)
                    for nome_algo, fn in algos.items():
                        tempo, comp, trocas, ord_, status = executar_uma(
                            fn, vetor, args.timeout
                        )
                        writer.writerow([
                            nome_cenario, tam, len(vetor), nome_algo, rep,
                            f"{tempo:.6f}", comp, trocas, int(ord_), status,
                        ])
                        arq.flush()
                        feitos += 1
                        print(
                            f"[{feitos}/{total_combos}] "
                            f"{nome_cenario:<18} {tam:<13} "
                            f"(n={len(vetor):>6}) {nome_algo:<14} "
                            f"rep{rep} -> {tempo:>8.4f}s "
                            f"cmp={comp:>12} trocas={trocas:>10} {status}"
                        )

    print(f"\nResultados gravados em {args.csv}")


if __name__ == "__main__":
    main()
