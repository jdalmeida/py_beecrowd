"""
Gera tabelas e graficos a partir do CSV de resultados produzido pelo benchmark.

Saidas:
- resultados/tabela_completa.md       : visao plana com reps + media por linha.
- resultados/tabelas_por_cenario.md   : layout do enunciado (1 sub-tabela por
                                        indicador, dentro de cada cenario).
- resultados/graficos/*.png           : graficos comparativos por cenario.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless: nao tenta abrir janela / Qt.

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from algoritmos import ALGORITMOS
from cenarios import CENARIOS, TAMANHOS

DIR = Path(__file__).parent / "resultados"
DIR_GRAFICOS = DIR / "graficos"


# ---------------------------------------------------------------------------
# Leitura do CSV
# ---------------------------------------------------------------------------
def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Indexacao auxiliar
# ---------------------------------------------------------------------------
def _por_chave(linhas: list[dict]):
    """Indexa em (algo, cenario, tamanho_label) -> {rep: linha}."""
    out = defaultdict(dict)
    for ln in linhas:
        chave = (ln["algoritmo"], ln["cenario"], ln["tamanho_label"])
        out[chave][int(ln["repeticao"])] = ln
    return out


def _media(reps: dict, campo: str):
    """Media dos valores numericos das repeticoes em que o status foi 'ok'."""
    valores = [
        float(r[campo]) for r in reps.values() if r["status"] == "ok"
    ]
    return float(np.mean(valores)) if valores else None


# ---------------------------------------------------------------------------
# Tabela completa (1 linha por algo x cen x tamanho)
# ---------------------------------------------------------------------------
def gerar_tabela_completa(linhas: list[dict], dest: Path) -> None:
    grupos = _por_chave(linhas)

    cols = [
        "Algoritmo", "Cenario", "Tamanho", "n",
        "t1 (s)", "t2 (s)", "t3 (s)", "t medio (s)",
        "cmp1", "cmp2", "cmp3", "cmp medio",
        "trc1", "trc2", "trc3", "trc medio",
    ]

    def fmt_t(v): return f"{v:.6f}" if v is not None else "—"
    def fmt_n(v): return f"{v:.0f}" if v is not None else "—"

    def linha_de(algo, cen, tam):
        reps = grupos.get((algo, cen, tam), {})
        if not reps:
            return None

        ts, cs, xs = [], [], []
        for r in (1, 2, 3):
            if r in reps and reps[r]["status"] == "ok":
                ts.append(float(reps[r]["tempo_s"]))
                cs.append(float(reps[r]["comparacoes"]))
                xs.append(float(reps[r]["trocas"]))
            else:
                ts.append(None); cs.append(None); xs.append(None)

        n = next(iter(reps.values()))["n"]
        return [
            algo, cen, tam, n,
            *(fmt_t(v) for v in ts), fmt_t(_media(reps, "tempo_s")),
            *(fmt_n(v) for v in cs), fmt_n(_media(reps, "comparacoes")),
            *(fmt_n(v) for v in xs), fmt_n(_media(reps, "trocas")),
        ]

    rows = []
    for algo in ALGORITMOS:
        for cen, info in CENARIOS.items():
            for tam in info["tamanhos"]:
                ln = linha_de(algo, cen, tam)
                if ln is not None:
                    rows.append(ln)

    with open(dest, "w", encoding="utf-8") as f:
        f.write("# Tabela completa de resultados\n\n")
        f.write("Cada linha agrega 3 repeticoes (sementes diferentes do mesmo cenario)\n")
        f.write("e mostra os valores individuais alem da media. Status 'TIMEOUT' aparece\n")
        f.write("como '—'.\n\n")
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "|".join(["---"] * len(cols)) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")

    print(f"Tabela completa: {dest}")


# ---------------------------------------------------------------------------
# Tabelas por cenario (layout do enunciado)
# ---------------------------------------------------------------------------
INDICADORES = [
    ("Tempo (s)",    "tempo_s",      "{:.6f}"),
    ("Comparacoes",  "comparacoes",  "{:.0f}"),
    ("Trocas",       "trocas",       "{:.0f}"),
]


def gerar_tabelas_por_cenario(linhas: list[dict], dest: Path) -> None:
    grupos = _por_chave(linhas)

    with open(dest, "w", encoding="utf-8") as f:
        f.write("# Tabelas comparativas por cenario\n\n")
        f.write(
            "Cada cenario possui 3 sub-tabelas (Tempo, Comparacoes, Trocas).\n"
            "Linhas: algoritmos. Colunas: tamanhos com 3 repeticoes (Rep 1/2/3)\n"
            "+ a media. '—' indica TIMEOUT ou ausencia de dado.\n\n"
        )

        for cen, info in CENARIOS.items():
            f.write(f"## Cenario: {cen}\n\n")
            tamanhos = info["tamanhos"]

            for nome_ind, campo, fmt in INDICADORES:
                f.write(f"### {nome_ind}\n\n")

                cab = ["Algoritmo"]
                for tam in tamanhos:
                    cab += [f"{tam} R1", f"{tam} R2", f"{tam} R3", f"{tam} media"]
                f.write("| " + " | ".join(cab) + " |\n")
                f.write("|" + "|".join(["---"] * len(cab)) + "|\n")

                for algo in ALGORITMOS:
                    cells = [algo]
                    for tam in tamanhos:
                        reps = grupos.get((algo, cen, tam), {})
                        for r in (1, 2, 3):
                            if r in reps and reps[r]["status"] == "ok":
                                cells.append(fmt.format(float(reps[r][campo])))
                            else:
                                cells.append("—")
                        med = _media(reps, campo)
                        cells.append(fmt.format(med) if med is not None else "—")
                    f.write("| " + " | ".join(cells) + " |\n")
                f.write("\n")

    print(f"Tabelas por cenario: {dest}")


# ---------------------------------------------------------------------------
# Graficos
# ---------------------------------------------------------------------------
CENARIOS_ESCALAVEIS = [
    "crescente", "decrescente", "repetido", "muitos repetidos", "longa",
]


def _medias_indexadas(linhas: list[dict]):
    """(cenario, tamanho_label, algoritmo) -> {tempo_s, comparacoes, trocas}."""
    grupos = defaultdict(list)
    for ln in linhas:
        if ln["status"] != "ok":
            continue
        chave = (ln["cenario"], ln["tamanho_label"], ln["algoritmo"])
        grupos[chave].append(ln)

    out = {}
    for chave, items in grupos.items():
        out[chave] = {
            "tempo_s":     float(np.mean([float(x["tempo_s"])     for x in items])),
            "comparacoes": float(np.mean([float(x["comparacoes"]) for x in items])),
            "trocas":      float(np.mean([float(x["trocas"])      for x in items])),
        }
    return out


def gerar_graficos(linhas: list[dict], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    med = _medias_indexadas(linhas)

    algos = list(ALGORITMOS.keys())
    tamanhos_ord = list(TAMANHOS.keys())

    # 1) Linhas: x = n, y = indicador medio, uma curva por algoritmo
    #    (escala log-log para acomodar O(n^2) vs O(n log n)).
    for cen in CENARIOS_ESCALAVEIS:
        for chave_ind, nome_ind in [
            ("tempo_s", "Tempo medio (s)"),
            ("comparacoes", "Comparacoes medias"),
            ("trocas", "Trocas medias"),
        ]:
            fig, ax = plt.subplots(figsize=(10, 6))
            algo_plotado = False
            for algo in algos:
                xs, ys = [], []
                for tam in tamanhos_ord:
                    chave = (cen, tam, algo)
                    if chave in med:
                        xs.append(TAMANHOS[tam])
                        ys.append(max(med[chave][chave_ind], 1e-12))
                if len(xs) >= 2:
                    ax.plot(xs, ys, marker="o", label=algo)
                    algo_plotado = True

            if not algo_plotado:
                plt.close(fig)
                continue

            ax.set_xlabel("n (tamanho do vetor)")
            ax.set_ylabel(nome_ind)
            ax.set_title(f"{nome_ind} - cenario '{cen}'")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.grid(True, which="both", linestyle="--", alpha=0.4)
            ax.legend(fontsize=8)
            fig.tight_layout()
            arq = dest / f"{chave_ind}_{cen.replace(' ', '_')}.png"
            fig.savefig(arq, dpi=130)
            plt.close(fig)
            print(f"Grafico: {arq}")

    # 2) Barras: para cada tamanho fixo, comparar algoritmos em cada cenario.
    for tam in ("media", "grande", "super_grande"):
        cenarios_disp = [
            c for c in CENARIOS_ESCALAVEIS
            if any((c, tam, a) in med for a in algos)
        ]
        if not cenarios_disp:
            continue

        fig, ax = plt.subplots(figsize=(11, 6))
        x = np.arange(len(algos))
        largura = 0.8 / len(cenarios_disp)
        for i, cen in enumerate(cenarios_disp):
            ys = [
                med.get((cen, tam, a), {}).get("tempo_s", 0)
                for a in algos
            ]
            ax.bar(x + i * largura, ys, largura, label=cen)

        ax.set_xticks(x + (len(cenarios_disp) - 1) * largura / 2)
        ax.set_xticklabels(algos, rotation=20, ha="right")
        ax.set_ylabel("Tempo medio (s)")
        ax.set_title(f"Tempo por algoritmo - tamanho {tam} (n={TAMANHOS[tam]})")
        ax.set_yscale("log")
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize=8)
        fig.tight_layout()
        arq = dest / f"barras_tempo_{tam}.png"
        fig.savefig(arq, dpi=130)
        plt.close(fig)
        print(f"Grafico: {arq}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--csv", default=str(DIR / "resultados.csv"))
    args = parser.parse_args(argv)

    DIR.mkdir(parents=True, exist_ok=True)
    DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)

    linhas = ler_csv(Path(args.csv))
    gerar_tabela_completa(linhas, DIR / "tabela_completa.md")
    gerar_tabelas_por_cenario(linhas, DIR / "tabelas_por_cenario.md")
    gerar_graficos(linhas, DIR_GRAFICOS)


if __name__ == "__main__":
    main()
