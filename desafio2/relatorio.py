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


# Paleta consistente entre todos os graficos: cada algoritmo mantem a mesma cor.
CORES_ALGOS = {
    "Insertion Sort": "#1f77b4",
    "Selection Sort": "#d62728",
    "Shell Sort":     "#ff7f0e",
    "Merge Sort":     "#2ca02c",
    "Quick Sort":     "#9467bd",
    "Radix Sort":     "#17becf",
}


def _fmt_ms(v_ms: float) -> str:
    """Rotulo amigavel para tempos em ms (auto-escala us/ms/s)."""
    if v_ms < 1:
        return f"{v_ms * 1000:.0f} us"
    if v_ms < 1000:
        return f"{v_ms:.1f} ms"
    return f"{v_ms / 1000:.2f} s"


def gerar_graficos(linhas: list[dict], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    med = _medias_indexadas(linhas)

    algos = list(ALGORITMOS.keys())
    tamanhos_ord = list(TAMANHOS.keys())

    # -----------------------------------------------------------------------
    # 1) Linhas log-log por cenario: tempo medio (ms), comparacoes, trocas.
    # -----------------------------------------------------------------------
    for cen in CENARIOS_ESCALAVEIS:
        for chave_ind, nome_ind, em_ms in [
            ("tempo_s",     "Tempo medio (ms)",   True),
            ("comparacoes", "Comparacoes medias", False),
            ("trocas",      "Trocas medias",      False),
        ]:
            fig, ax = plt.subplots(figsize=(10, 6))
            algo_plotado = False
            for algo in algos:
                xs, ys = [], []
                for tam in tamanhos_ord:
                    chave = (cen, tam, algo)
                    if chave in med:
                        v = med[chave][chave_ind]
                        if em_ms:
                            v *= 1000.0  # s -> ms
                        xs.append(TAMANHOS[tam])
                        ys.append(max(v, 1e-9))
                if len(xs) >= 2:
                    ax.plot(
                        xs, ys, marker="o", linewidth=2, markersize=7,
                        color=CORES_ALGOS.get(algo), label=algo,
                    )
                    algo_plotado = True

            if not algo_plotado:
                plt.close(fig)
                continue

            ax.set_xlabel("n (tamanho do vetor)")
            ax.set_ylabel(nome_ind)
            ax.set_title(f"{nome_ind} - cenario '{cen}' (escala log-log)")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.grid(True, which="both", linestyle="--", alpha=0.4)
            ax.legend(fontsize=9, loc="best", framealpha=0.9)
            fig.tight_layout()
            sufixo = "tempo_ms" if em_ms else chave_ind
            arq = dest / f"{sufixo}_{cen.replace(' ', '_')}.png"
            fig.savefig(arq, dpi=130)
            plt.close(fig)
            print(f"Grafico: {arq}")

    # -----------------------------------------------------------------------
    # 2) Barras agrupadas por tamanho: tempo medio (ms) de cada algoritmo
    #    em cada cenario; rotulo de valor no topo de cada barra.
    # -----------------------------------------------------------------------
    for tam in ("media", "grande", "super_grande"):
        cenarios_disp = [
            c for c in CENARIOS_ESCALAVEIS
            if any((c, tam, a) in med for a in algos)
        ]
        if not cenarios_disp:
            continue

        fig, ax = plt.subplots(figsize=(13, 7))
        x = np.arange(len(algos))
        largura = 0.8 / len(cenarios_disp)
        cmap = plt.get_cmap("tab10")
        for i, cen in enumerate(cenarios_disp):
            ys_ms = [
                med.get((cen, tam, a), {}).get("tempo_s", 0) * 1000.0
                for a in algos
            ]
            barras = ax.bar(
                x + i * largura, ys_ms, largura,
                label=cen, color=cmap(i),
            )
            for rect, valor in zip(barras, ys_ms):
                if valor <= 0:
                    continue
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    valor * 1.05,
                    _fmt_ms(valor),
                    ha="center", va="bottom",
                    fontsize=7, rotation=90,
                )

        ax.set_xticks(x + (len(cenarios_disp) - 1) * largura / 2)
        ax.set_xticklabels(algos, rotation=20, ha="right")
        ax.set_ylabel("Tempo medio (ms)")
        ax.set_title(f"Tempo por algoritmo - tamanho {tam} (n={TAMANHOS[tam]})")
        ax.set_yscale("log")
        ax.grid(True, axis="y", which="both", linestyle="--", alpha=0.4)
        ax.legend(fontsize=9, loc="upper left", framealpha=0.9)
        fig.tight_layout()
        arq = dest / f"barras_tempo_{tam}.png"
        fig.savefig(arq, dpi=130)
        plt.close(fig)
        print(f"Grafico: {arq}")

    # -----------------------------------------------------------------------
    # 3) Resumo por algoritmo: cada algoritmo tem um sub-plot mostrando como
    #    o tempo medio (ms) cresce com n para cada cenario. Da pra comparar
    #    o comportamento dentro de um mesmo algoritmo de forma direta.
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex=True, sharey=True)
    cmap_cen = plt.get_cmap("tab10")
    for ax, algo in zip(axes.flat, algos):
        for i, cen in enumerate(CENARIOS_ESCALAVEIS):
            xs, ys = [], []
            for tam in tamanhos_ord:
                chave = (cen, tam, algo)
                if chave in med:
                    xs.append(TAMANHOS[tam])
                    ys.append(max(med[chave]["tempo_s"] * 1000.0, 1e-9))
            if len(xs) >= 2:
                ax.plot(
                    xs, ys, marker="o", linewidth=1.8,
                    color=cmap_cen(i), label=cen,
                )
        ax.set_title(algo, fontsize=11)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(True, which="both", linestyle="--", alpha=0.4)

    for ax in axes[-1, :]:
        ax.set_xlabel("n")
    for ax in axes[:, 0]:
        ax.set_ylabel("Tempo medio (ms)")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="lower center", ncol=len(CENARIOS_ESCALAVEIS),
        fontsize=9, bbox_to_anchor=(0.5, -0.01),
    )
    fig.suptitle("Tempo medio (ms) por algoritmo - cenarios sobrepostos",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    arq = dest / "resumo_tempo_ms_por_algoritmo.png"
    fig.savefig(arq, dpi=130)
    plt.close(fig)
    print(f"Grafico: {arq}")

    # -----------------------------------------------------------------------
    # 4) Heatmap: tempo medio (ms) com algoritmos nas linhas e
    #    (cenario, tamanho) nas colunas. Otimo para um overview rapido.
    # -----------------------------------------------------------------------
    colunas = []
    for cen in CENARIOS_ESCALAVEIS:
        for tam in tamanhos_ord:
            if any((cen, tam, a) in med for a in algos):
                colunas.append((cen, tam))

    matriz = np.full((len(algos), len(colunas)), np.nan)
    for i, algo in enumerate(algos):
        for j, (cen, tam) in enumerate(colunas):
            chave = (cen, tam, algo)
            if chave in med:
                matriz[i, j] = med[chave]["tempo_s"] * 1000.0

    fig, ax = plt.subplots(figsize=(max(10, 0.7 * len(colunas)), 5.5))
    matriz_log = np.log10(np.where(np.isnan(matriz) | (matriz <= 0),
                                    np.nan, matriz))
    im = ax.imshow(matriz_log, aspect="auto", cmap="viridis")

    ax.set_xticks(range(len(colunas)))
    ax.set_xticklabels(
        [f"{c}\n{t}" for c, t in colunas], rotation=30, ha="right", fontsize=8,
    )
    ax.set_yticks(range(len(algos)))
    ax.set_yticklabels(algos)
    ax.set_title("Tempo medio (ms) - heatmap (cor em log10 ms)")

    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = matriz[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center",
                        color="#444444", fontsize=8)
            else:
                # Threshold acima da metade da escala -> fundo claro -> texto escuro.
                vmin, vmax = np.nanmin(matriz_log), np.nanmax(matriz_log)
                norm = (matriz_log[i, j] - vmin) / max(vmax - vmin, 1e-9)
                cor_txt = "black" if norm > 0.55 else "white"
                ax.text(j, i, _fmt_ms(v), ha="center", va="center",
                        color=cor_txt, fontsize=7)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("log10(tempo em ms)")
    fig.tight_layout()
    arq = dest / "heatmap_tempo_ms.png"
    fig.savefig(arq, dpi=130)
    plt.close(fig)
    print(f"Grafico: {arq}")

    # -----------------------------------------------------------------------
    # 5) Ranking horizontal: top algoritmos no maior tamanho disponivel,
    #    um sub-plot por cenario. Mostra com clareza quem e mais rapido em
    #    cada cenario com o valor em ms ao lado da barra.
    # -----------------------------------------------------------------------
    def _fmt_inteiro(v: float) -> str:
        """Numero grande de comparacoes/trocas em formato amigavel."""
        if v >= 1e9:
            return f"{v / 1e9:.2f} B"
        if v >= 1e6:
            return f"{v / 1e6:.2f} M"
        if v >= 1e3:
            return f"{v / 1e3:.1f} k"
        return f"{v:.0f}"

    def _gerar_ranking(campo: str, titulo: str, eixo_x: str,
                       fmt_valor, escala_valor, arquivo: str) -> None:
        fig, axes = plt.subplots(
            len(CENARIOS_ESCALAVEIS), 1,
            figsize=(12, 3.0 * len(CENARIOS_ESCALAVEIS)),
            sharex=False,
        )
        if len(CENARIOS_ESCALAVEIS) == 1:
            axes = [axes]

        for ax, cen in zip(axes, CENARIOS_ESCALAVEIS):
            # Maior tamanho com mais cobertura de algoritmos (em empate,
            # vence o n maior).
            melhor_tam, melhor_cobertura = None, -1
            for tam in tamanhos_ord:
                cobertura = sum(1 for a in algos if (cen, tam, a) in med)
                if cobertura == 0:
                    continue
                if (cobertura > melhor_cobertura
                        or (cobertura == melhor_cobertura and TAMANHOS[tam]
                            > TAMANHOS[melhor_tam])):
                    melhor_tam, melhor_cobertura = tam, cobertura
            tam_alvo = melhor_tam
            if tam_alvo is None:
                ax.set_visible(False)
                continue

            pares = []
            for a in algos:
                chave = (cen, tam_alvo, a)
                if chave in med:
                    pares.append((a, escala_valor(med[chave][campo])))
                else:
                    pares.append((a + " (TIMEOUT)", float("nan")))
            pares.sort(key=lambda x: (np.isnan(x[1]), x[1]))
            nomes = [p[0] for p in pares]
            valores = [p[1] for p in pares]

            cores = [
                CORES_ALGOS.get(n.replace(" (TIMEOUT)", ""), "#888888")
                for n in nomes
            ]
            valores_plot = [
                # Em escala log, 0 nao plota: mostra um sliver minimo.
                max(v, 1e-9) if not np.isnan(v) else 0.0
                for v in valores
            ]
            barras = ax.barh(nomes, valores_plot, color=cores)
            ax.set_xscale("log")
            ax.set_title(
                f"{cen} (tamanho {tam_alvo}, n={TAMANHOS[tam_alvo]})",
                fontsize=10,
            )
            ax.grid(True, axis="x", which="both", linestyle="--", alpha=0.4)
            for rect, v in zip(barras, valores):
                if np.isnan(v):
                    ax.text(
                        1, rect.get_y() + rect.get_height() / 2,
                        "TIMEOUT", va="center", fontsize=8, color="#777777",
                    )
                elif v <= 0:
                    ax.text(
                        1, rect.get_y() + rect.get_height() / 2,
                        "0", va="center", fontsize=8, color="#555555",
                    )
                else:
                    ax.text(
                        v * 1.05, rect.get_y() + rect.get_height() / 2,
                        fmt_valor(v), va="center", fontsize=8,
                    )
            ax.set_xlabel(eixo_x)

        fig.suptitle(titulo, fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        arq = dest / arquivo
        fig.savefig(arq, dpi=130)
        plt.close(fig)
        print(f"Grafico: {arq}")

    _gerar_ranking(
        campo="tempo_s",
        titulo="Ranking de tempo medio (ms) por cenario - maior n disponivel",
        eixo_x="Tempo medio (ms, escala log)",
        fmt_valor=_fmt_ms,
        escala_valor=lambda v: v * 1000.0,
        arquivo="ranking_tempo_ms.png",
    )
    _gerar_ranking(
        campo="comparacoes",
        titulo="Ranking de comparacoes medias por cenario - maior n disponivel",
        eixo_x="Comparacoes medias (escala log)",
        fmt_valor=_fmt_inteiro,
        escala_valor=lambda v: v,
        arquivo="ranking_comparacoes.png",
    )
    _gerar_ranking(
        campo="trocas",
        titulo="Ranking de trocas medias por cenario - maior n disponivel",
        eixo_x="Trocas medias (escala log)",
        fmt_valor=_fmt_inteiro,
        escala_valor=lambda v: v,
        arquivo="ranking_trocas.png",
    )


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
