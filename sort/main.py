import numpy as np
import time  as t

def gerar_emails_aleatorios(n):
    dominios = ["gmail.com", "outlook.com", "spam.net", "promocao.org", "teste.io"]
    # Gerar prefixos aleatórios usando numpy
    letras = np.array(list('abcdefghijklmnopqrstuvwxyz'))
    # Criar n prefixos de 8 letras cada
    prefixos_matriz = np.random.choice(letras, size=(n, 8))
    prefixos = ["".join(linha) for linha in prefixos_matriz]

    emails = [f"{p}@{np.random.choice(dominios)}" for p in prefixos]
    return np.array(emails)


def radix_sort(emails, pos=0):
    if len(emails) <= 1:
        return emails

    buckets = {}
    for email in emails:
        char = email[pos] if pos < len(email) else ''
        buckets.setdefault(char, []).append(email)

    result = []
    for key in sorted(buckets.keys()):
        if key == '':
            result.extend(buckets[key])
        else:
            result.extend(radix_sort(buckets[key], pos + 1))

    return result


def sort_rapido(emails):
    # Timsort implementado em Python puro.
    # 1) acha "runs" naturais (trechos já ordenados),
    # 2) estende runs curtos com insertion sort binário até minrun,
    # 3) empilha runs e funde respeitando os invariantes do Timsort
    #    (X > Y+Z e Y > Z para os 3 topos), fundindo sempre os menores.
    arr = list(emails)
    n = len(arr)
    if n < 2:
        return arr

    def minrun_length(x):
        r = 0
        while x >= 64:
            r |= x & 1
            x >>= 1
        return x + r

    def insertion_sort(a, lo, hi):
        # Ordena a[lo:hi] in-place via busca binária + shift.
        for i in range(lo + 1, hi):
            pivot = a[i]
            left, right = lo, i
            while left < right:
                mid = (left + right) >> 1
                if pivot < a[mid]:
                    right = mid
                else:
                    left = mid + 1
            j = i
            while j > left:
                a[j] = a[j - 1]
                j -= 1
            a[left] = pivot

    def count_run(a, lo, hi):
        # Retorna o tamanho do run que começa em lo. Inverte se descendente.
        if lo + 1 == hi:
            return 1
        end = lo + 1
        if a[lo + 1] < a[lo]:
            while end < hi and a[end] < a[end - 1]:
                end += 1
            a[lo:end] = a[lo:end][::-1]
        else:
            while end < hi and a[end] >= a[end - 1]:
                end += 1
        return end - lo

    def merge(a, lo, mid, hi):
        # Funde a[lo:mid] com a[mid:hi] usando um buffer do lado menor.
        left = a[lo:mid]
        right = a[mid:hi]
        i = j = 0
        k = lo
        ll, rl = len(left), len(right)
        while i < ll and j < rl:
            if right[j] < left[i]:
                a[k] = right[j]
                j += 1
            else:
                a[k] = left[i]
                i += 1
            k += 1
        while i < ll:
            a[k] = left[i]
            i += 1
            k += 1
        while j < rl:
            a[k] = right[j]
            j += 1
            k += 1

    minrun = minrun_length(n)
    runs = []  # pilha de (início, tamanho)
    i = 0
    while i < n:
        rl = count_run(arr, i, n)
        if rl < minrun:
            force = min(minrun, n - i)
            insertion_sort(arr, i, i + force)
            rl = force
        runs.append([i, rl])
        i += rl

        # Mantém invariantes fundindo quando necessário.
        while len(runs) > 1:
            if len(runs) >= 3:
                xs, xl = runs[-3]
                ys, yl = runs[-2]
                zs, zl = runs[-1]
                if xl <= yl + zl:
                    if xl < zl:
                        merge(arr, xs, ys, ys + yl)
                        runs[-3] = [xs, xl + yl]
                        runs.pop(-2)
                    else:
                        merge(arr, ys, zs, zs + zl)
                        runs[-2] = [ys, yl + zl]
                        runs.pop()
                    continue
            ys, yl = runs[-2]
            zs, zl = runs[-1]
            if yl <= zl:
                merge(arr, ys, zs, zs + zl)
                runs[-2] = [ys, yl + zl]
                runs.pop()
                continue
            break

    # Funde o que sobrou na pilha.
    while len(runs) > 1:
        ys, yl = runs[-2]
        zs, zl = runs[-1]
        merge(arr, ys, zs, zs + zl)
        runs[-2] = [ys, yl + zl]
        runs.pop()

    return arr


def formatar_tempo(segundos):
    return f"{segundos*1000:.2f} ms" if segundos < 1 else f"{segundos:.4f} s"


# 1. Definir quantidade
N_EMAILS = 200000

# 2. Gerar base de dados de emails
base_dados = gerar_emails_aleatorios(N_EMAILS)

# 3. Mostrar amostra antes do sort
print("Antes do sort:")
for e in base_dados[:20]:
    print(e)

# 4. Radix sort
start = t.perf_counter()
ordenado_radix = radix_sort(base_dados)
tempo_radix = t.perf_counter() - start

# 5. Sort rápido (Timsort)
start = t.perf_counter()
ordenado_rapido = sort_rapido(base_dados)
tempo_rapido = t.perf_counter() - start

# 6. Comparação
print("\n\n=== COMPARAÇÃO ===")
print(f"radix_sort  (MSD recursivo, Python puro): {formatar_tempo(tempo_radix)}")
print(f"sort_rapido (Timsort, Python puro):       {formatar_tempo(tempo_rapido)}")
razao = tempo_radix / tempo_rapido
if razao >= 1:
    print(f"\nsort_rapido foi {razao:.2f}x mais rápido que o radix_sort")
else:
    print(f"\nradix_sort foi {1/razao:.2f}x mais rápido que o sort_rapido")
print(f"Resultados idênticos: {list(ordenado_radix) == list(ordenado_rapido)}")

print("\n\nDepois do sort:")
for e in ordenado_rapido[:20]:
    print(str(e))
