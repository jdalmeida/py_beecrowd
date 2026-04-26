# Desafio 2 — Análise comparativa de algoritmos de ordenação (nível **big**)

Implementação em Python 3 dos seis algoritmos pedidos no enunciado
(Insertion, Selection, Shell, Merge, Quick e Radix Sort), com instrumentação
para contar **comparações**, **trocas** e **tempo de execução**, executada de
forma automatizada nos **8 cenários** definidos pelo desafio e nas **4 massas
de dados** previstas (1 000, 10 000, 50 000 e 100 000 elementos).

## Estrutura do projeto

| Arquivo | Função |
|---|---|
| `algoritmos.py` | Implementações dos 6 algoritmos + classe `Contador` + tabela Big-O |
| `cenarios.py` | Geradores dos 8 cenários (sementes determinísticas) + tamanhos das massas |
| `benchmark.py` | Runner: executa todas as combinações e grava `resultados/resultados.csv` |
| `relatorio.py` | Lê o CSV e gera tabelas Markdown + gráficos PNG |
| `main.py` | Atalho: roda `benchmark.py` e em seguida `relatorio.py` |
| `resultados/` | CSV bruto, tabelas e gráficos gerados |

## Como executar

```bash
# Tudo de uma vez (até super grande):
python3 main.py --reps 3 --timeout 900

# Ou em duas etapas, controlando o que rodar:
python3 benchmark.py --max-tamanho grande --reps 3 --timeout 900
python3 benchmark.py --append --min-tamanho super_grande \
        --algoritmos "Shell Sort" "Merge Sort" "Quick Sort" "Radix Sort" \
        --reps 3 --timeout 600
python3 relatorio.py
```

> **Por que duas etapas?** Em Python puro, Insertion/Selection em vetor de
> 100 000 elementos custam dezenas de minutos por execução (ver discussão
> adiante). Roda-se a massa _super grande_ apenas para os algoritmos
> sub-quadráticos; os O(n²) ficam representados até _grande_ (50 000),
> suficiente para enxergar a curva de crescimento.

---

## 1. Como foram gerados os vetores aleatórios?

Foi usado `numpy.random.default_rng(seed)` (PCG64) com **seed determinística**
calculada por `hash((cenario, tamanho, repeticao)) % 2³²`. Isso garante:

- **Reprodutibilidade**: rodar duas vezes produz o mesmo vetor.
- **Mesmo vetor entre algoritmos**: como a seed depende apenas de
  `(cenario, tamanho, repeticao)`, os 6 algoritmos recebem exatamente o
  mesmo vetor de entrada para uma dada repetição.
- **Variação entre repetições**: cada repetição usa uma seed diferente,
  cumprindo o requisito de "no mínimo, três casos de teste para cada cenário".

Detalhes por cenário (`cenarios.py`):

| Cenário | Como o vetor é construído |
|---|---|
| aleatória pequena | inteiros uniformes em `[0, 1 000 000)` |
| crescente | `cumsum` de pequenos incrementos aleatórios (vetor já ordenado) |
| decrescente | igual ao crescente, mas invertido |
| repetido | um único valor sorteado replicado n vezes |
| vazia | `[]` |
| um item | um único inteiro sorteado |
| muitos repetidos | apenas `√n` (cap 10) valores distintos |
| longa | aleatório uniforme nas massas média/grande/super grande |

## 2. Mesma situação inicial para todos os algoritmos

Para cada `(cenario, tamanho, repeticao)` o gerador produz **um único vetor**.
Antes de chamar cada algoritmo, o runner faz `copia = list(vetor)` (cópia rasa,
suficiente porque os elementos são `int` imutáveis). Assim os 6 algoritmos
recebem o mesmo conteúdo na mesma ordem. Esse pareamento controla a
variabilidade do experimento: diferenças observadas vêm do algoritmo, não da
entrada. (`benchmark.py:executar_uma`)

## 3. Adaptação dos algoritmos: contagem de comparações, trocas e tempo

### Comparações e trocas

Foi criada a classe `Contador` (`algoritmos.py`) com três métodos:

```python
c.cmp(a, b)        # retorna -1/0/1 e incrementa comparacoes
c.menor(a, b)      # bool; conta 1 comparacao
c.trocar(v, i, j)  # swap em v; conta 1 troca
```

Cada algoritmo foi reescrito para usar esses pontos de medição. Onde a
operação é uma cópia que substitui um swap (caso clássico de Insertion,
Shell e Merge — eles deslocam, não trocam), a movimentação foi contabilizada
como troca, seguindo a definição do enunciado: _"quantidade de vezes que uma
dupla de valores trocou de posição no vetor"_. Isso é coerente com a
literatura: Sedgewick & Wayne (2011) discutem que, para insertion/shell, o
custo dominante é o "deslocamento", contado como move/swap.

Detalhe específico: `Selection Sort` faz exatamente n − 1 trocas no pior
caso e ~n²/2 comparações sempre — confirmado nos resultados.

### Tempo

`time.perf_counter()` — relógio monotônico de mais alta resolução disponível
no SO (no Linux, baseia-se em `CLOCK_MONOTONIC`). Não é afetado por ajustes
de relógio (NTP) e tem precisão sub-microssegundo. Antes de cada medição:

- `gc.disable()` para evitar pausa do garbage collector durante o trecho
  cronometrado;
- `Contador()` reinicializado;
- a cópia é feita **antes** de `perf_counter()` — só a ordenação é cronometrada.

Cada execução tem _time-budget_ configurável (`--timeout`); se exceder,
`SIGALRM` aborta e a linha é gravada com `status=TIMEOUT`.

### Configuração da máquina

| | |
|---|---|
| CPU | Intel Core Ultra 7 155U (14 threads, 4.8 GHz boost) |
| Cache L3 | 12 MiB |
| RAM | 14 GiB |
| SO | Linux 6.17 (Ubuntu) |
| Python | 3.13.7 (CPython, sem JIT) |
| numpy | 2.2.4 |

> Observação: como CPython interpreta bytecode, todas as constantes de tempo
> são ~50–100× maiores do que seriam em C. O importante para a análise é a
> **forma da curva** (crescimento), não o valor absoluto.

## 4. Classificação Big-O

Tabela retirada de Cormen et al. (2009) e Sedgewick & Wayne (2011),
reproduzida em `algoritmos.py`:

| Algoritmo | Melhor | Médio | Pior | Memória extra |
|---|---|---|---|---|
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) |
| Shell Sort (Knuth) | O(n log n) | ~O(n^1.3) | O(n^1.5) | O(1) |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) |
| Quick Sort (3-way + mediana) | O(n log n) | O(n log n) | O(n²)¹ | O(log n) |
| Radix Sort (LSD) | O(d·(n+b)) | O(d·(n+b)) | O(d·(n+b)) | O(n+b) |

¹ Pior caso de Quick Sort fica raríssimo com partição 3-way + pivô
mediana-de-três amostrado aleatoriamente; entradas já ordenadas, repetidas e
decrescentes — armadilhas clássicas — caem para O(n log n) na prática.
`d` = nº de dígitos, `b` = base (10 nesta implementação).

## 5. Resultados

Os arquivos completos ficam em `resultados/` após executar o benchmark:

- `resultados.csv` — uma linha por execução (cenário, tamanho, algoritmo,
  rep, tempo, comparações, trocas, status).
- `tabela_completa.md` — visão plana com 3 reps + média por linha.
- `tabelas_por_cenario.md` — layout do enunciado: para **cada cenário**, três
  sub-tabelas (Tempo / Comparações / Trocas) com algoritmos nas linhas e
  tamanhos × (R1 / R2 / R3 / média) nas colunas.
- `graficos/` — PNGs:
  - `tempo_s_<cenario>.png`, `comparacoes_<cenario>.png`,
    `trocas_<cenario>.png` — curvas log-log do indicador vs. _n_ por
    algoritmo, em cada cenário escalável.
  - `barras_tempo_<tamanho>.png` — comparação de tempos entre algoritmos
    para um tamanho fixo, agrupado por cenário.

### 5.1 Resumo executivo — escala em vetor aleatório (`longa`)

Tempo médio (3 repetições) em segundos. "—" indica execução abortada por
estouro do _time-budget_ de 600 s (ver §6).

| Algoritmo | média (10k) | grande (50k) | super_grande (100k) |
|---|---|---|---|
| Insertion Sort | 7,4236 s | 189,3092 s | — |
| Selection Sort | 8,8979 s | 225,0782 s | — |
| Shell Sort | 0,0683 s | 0,5188 s | 1,3175 s |
| Merge Sort | 0,0561 s | 0,3106 s | 0,6825 s |
| Quick Sort | 0,0685 s | 0,4280 s | 0,9165 s |
| Radix Sort | 0,0295 s | 0,1558 s | 0,3383 s |

A relação `(50k → 10k) ≈ 25×` em Insertion/Selection confirma o crescimento
**quadrático** (5² = 25). Para Merge, Shell, Quick e Radix o crescimento é
~5–9×, alinhado a `O(n log n)` / `O(n)`.

### 5.2 Sensibilidade ao formato da entrada (n = 50 000)

Tempo médio (s) por cenário, em massa **grande**:

| Algoritmo | crescente | decrescente | repetido | muitos repetidos | longa |
|---|---|---|---|---|---|
| Insertion Sort | 0,0113 | **370,4273** | 0,0113 | 169,7197 | 189,3092 |
| Selection Sort | 221,4195 | 227,0243 | 224,6910 | 225,9670 | 225,0782 |
| Shell Sort | 0,0963 | 0,1783 | 0,0999 | 0,1682 | 0,5188 |
| Merge Sort | 0,1880 | 0,2580 | 0,1991 | 0,2947 | 0,3106 |
| Quick Sort | 0,4160 | 0,4181 | **0,0141** | 0,0701 | 0,4280 |
| Radix Sort | 0,1401 | 0,1375 | 0,1577 | 0,1551 | 0,1558 |

Pontos a observar:

- **Insertion** vai de 0,011 s (já ordenado) a 370 s (invertido) — fator de
  ~33 000× só pelo formato da entrada. É o exemplo perfeito de algoritmo
  _input-sensitive_.
- **Selection** é praticamente constante (sempre ~225 s) — confirma que
  faz n·(n−1)/2 comparações independentemente do conteúdo.
- **Quick Sort** explora o cenário `repetido` em 14 ms, ~30× mais rápido
  que em vetor aleatório, graças à partição 3-way (todos os elementos caem
  na faixa "igual ao pivô" em uma única passada).
- **Radix Sort** é praticamente insensível ao conteúdo — sempre 7 passes
  de counting sort.

## 6. Discussão dos resultados (com base na literatura)

**Por que Insertion vence em vetores quase ordenados?** No melhor caso
(crescente), a contagem é apenas n − 1 comparações e zero trocas: o `while`
interno aborta na primeira comparação. Isso é o comportamento O(n) descrito
em Sedgewick & Wayne (2011, p. 250) e é empiricamente o algoritmo mais rápido
nos cenários `crescente` e `repetido` em massas pequenas.

**Por que Selection é insensível à entrada?** Sua estrutura faz
exatamente n·(n−1)/2 comparações independentemente do conteúdo do vetor.
A coluna de comparações na tabela é constante por tamanho — a literatura
chama isso de "algoritmo oblívio" (Cormen et al., 2009, §2.2). Mesmo em
vetor já ordenado, paga-se o pior caso: por isso Selection Sort raramente é
usado em produção.

**Por que Shell Sort se aproxima de O(n log n) com gap de Knuth?** A
sequência 1, 4, 13, 40, 121… (Knuth 1973) limita o número de inversões
restantes em cada passada, e empiricamente a complexidade observada fica em
torno de O(n^1,3). Os gráficos confirmam: a curva de Shell fica visivelmente
abaixo das curvas O(n²) e bem próxima das O(n log n) para os tamanhos
testados.

**Quick Sort vs Merge Sort.** Para vetores aleatórios, Quick costuma vencer
porque executa _in-place_, com melhor uso de cache (Sedgewick & Wayne,
2011, p. 297). Merge ganha estabilidade e garantia O(n log n) no pior caso,
ao custo de O(n) memória extra e mais movimentações. Em vetores
**decrescentes** ou **com muitos repetidos**, a partição 3-way (Dutch
National Flag, Sedgewick 1998) elimina o caso degenerado clássico do
Quicksort — visível nos resultados: o número de comparações nesses cenários
fica próximo de n para o `repetido` (cada elemento é classificado como
"igual ao pivô" em uma passada).

**Radix Sort não compara, conta passes.** Ele faz `d` passes de counting
sort por dígito, totalizando O(d·(n+b)). Para inteiros até 10⁶ (`d=7`,
`b=10`), é O(7·(n+10)) ≈ O(n). Como esperado, comparações ≈ n − 1 (apenas
para achar o `max`) e trocas crescem linearmente. Em massas grandes de
inteiros, é muitas vezes o mais rápido — mas perde a vantagem se as
chaves forem strings longas ou floats arbitrários, conforme alerta Cormen
et al. (2009, §8.3).

**Por que algumas células ficam vazias na coluna `super_grande`?** Em Python
puro, n=100 000 com Insertion ou Selection demandaria ~15–25 minutos por
execução; o benchmark aborta após o `--timeout` configurado. A literatura
explica: a constante multiplicativa do CPython (interpretado, sem JIT) é
~50× a de uma implementação compilada, e isso multiplica o termo n² do
Insertion/Selection a um custo proibitivo.

## 7. Referências

1. **Oliveira, A. B.; Prada, A.; Silva, R. R.** _Métodos de Ordenação
   Interna_. Florianópolis: Visual Books, 2002.
2. **Ascencio, A. F. G.; Araújo, G. S.** _Estrutura de dados: algoritmos,
   análise da complexidade e implementações em Java, C/C++_. São Paulo:
   Pearson Prentice Hall, 2010 — capítulo 2.
3. **Cormen, T. H.; Leiserson, C. E.; Rivest, R. L.; Stein, C.**
   _Introduction to Algorithms_. 3ª ed., MIT Press, 2009 — capítulos 2, 7,
   8 (Insertion, Quick e Radix).
4. **Sedgewick, R.; Wayne, K.** _Algorithms_. 4ª ed., Addison-Wesley, 2011 —
   capítulo 2 (ordenação) e [`algs4.cs.princeton.edu`](https://algs4.cs.princeton.edu/).
5. **Knuth, D. E.** _The Art of Computer Programming, vol. 3: Sorting and
   Searching_. 2ª ed., Addison-Wesley, 1998 — sequência de gaps (5.2.1).
6. **Sedgewick, R.** "Quicksort is optimal", 1998 (partição _3-way_ /
   _Dutch National Flag_).
7. Simuladores usados para validar comportamento: VisuAlgo (Halim &
   Steven), [Data Structure Visualizations](https://www.cs.usfca.edu/~galles/visualization/Algorithms.html)
   (Galles), [AlgoVis.io](https://algovis.io/).
