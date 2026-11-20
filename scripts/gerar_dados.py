"""Gera dados fictícios para o painel de metas (dados.json).

Os números não são de nenhuma empresa real. O script cria 10 lojas de uma
franqueada fictícia (Grupo Horizonte, da rede fictícia Aurora Cosméticos) com
sazonalidade típica de varejo de cosméticos (Dia das Mães, Dia dos Namorados,
Dia dos Pais, Black Friday e Natal) e algumas tendências para o painel ter o
que mostrar: boletos caindo, boleto médio subindo e lojas com desempenhos
diferentes.

Uso:  python scripts/gerar_dados.py
Saída: dados.json na raiz do projeto. A semente é fixa, então o resultado é
sempre o mesmo.
"""
import calendar
import datetime as dt
import json
import random
from pathlib import Path

random.seed(2026)

HOJE = dt.date(2026, 11, 18)        # data de demonstração do painel
ULTIMO_DIA_COM_VENDA = HOJE - dt.timedelta(days=1)
FERIADOS = {dt.date(2026, 11, 2), dt.date(2026, 11, 20), dt.date(2026, 12, 25)}
LOJAS_RUA = {"RCE", "RFL", "AVB"}   # fecham em feriado de dia útil

# código: (faturamento 2025 em R$, boleto médio 2025, peças por boleto,
#          crescimento 2026, variação de boletos 2026, peso planejado 2027)
LOJAS = {
    "RCE": (1_150_000, 112, 2.05, -0.05, -0.10, 0.052),
    "HNO": (3_650_000, 98, 2.30, 0.06, -0.01, 0.188),
    "RFL": (2_050_000, 118, 2.10, 0.02, -0.06, 0.106),
    "AVB": (2_180_000, 121, 2.15, 0.00, -0.08, 0.104),
    "MSU": (1_020_000, 92, 2.40, 0.08, 0.03, 0.071),
    "SPQ": (2_300_000, 135, 1.95, 0.05, -0.02, 0.112),
    "MPQ": (1_620_000, 95, 2.35, 0.03, -0.04, 0.083),
    "SLA": (2_000_000, 128, 2.00, 0.09, 0.01, 0.110),
    "SCO": (1_850_000, 124, 2.05, -0.02, -0.07, 0.094),
    "MAV": (None, 100, 2.30, None, None, 0.079),   # loja nova, abriu em fev/2026
}
MAV_MENSAL_MADURO = 135_000  # venda mensal média da loja nova depois de 3 meses

# peso de cada mês no ano (Dia das Mães em maio, Dia dos Pais em agosto, Natal em dezembro)
SAZONAL = [0.78, 0.76, 0.92, 0.95, 1.38, 1.02, 0.88, 1.07, 0.92, 0.98, 1.10, 1.94]
SAZ_SOMA = sum(SAZONAL)


def ruido(pct):
    return 1 + random.uniform(-pct, pct)


def dias_loja(ano, mes, loja, desde=None, ate=None):
    """Dias de loja aberta (segunda a sábado) no mês, opcionalmente entre duas datas."""
    n = 0
    for d in range(1, calendar.monthrange(ano, mes)[1] + 1):
        dia = dt.date(ano, mes, d)
        if desde and dia < desde:
            continue
        if ate and dia > ate:
            continue
        if dia.weekday() == 6:
            continue
        if loja in LOJAS_RUA and dia in FERIADOS:
            continue
        n += 1
    return n


def arred(v, casas=2):
    return None if v is None else round(v, casas)


rows = []
mes_atual = HOJE.month
for loja, (fat25, bm25, pd25, cresc, var_bol, _peso) in LOJAS.items():
    tendencia = random.uniform(-0.015, 0.015)  # piora ou melhora ao longo do ano
    for mes in range(1, 13):
        r = {"mes": mes, "loja": loja}
        # ---- 2025
        if fat25:
            fin25 = fat25 * SAZONAL[mes - 1] / SAZ_SOMA * ruido(0.05)
            bm = bm25 * (1.12 if mes in (5, 12) else 1) * ruido(0.03)
            bol25 = fin25 / bm
            fis25 = bol25 * pd25 * ruido(0.03)
        else:
            fin25 = bol25 = fis25 = None
        # ---- 2026 (realizado até ontem)
        fin26 = bol26 = fis26 = None
        if mes <= mes_atual:
            if fat25:
                g = cresc + tendencia * (mes - 6) / 6 + random.uniform(-0.035, 0.035)
                vb = var_bol + random.uniform(-0.03, 0.03)
                cheio = fin25 * (1 + g)
                b_cheio = bol25 * (1 + vb)
                f_cheio = fis25 * (1 + vb) * ruido(0.03)
            elif mes >= 2:
                rampa = {2: 0.55, 3: 0.8, 4: 0.92}.get(mes, 1.0)
                cheio = MAV_MENSAL_MADURO * rampa * SAZONAL[mes - 1] / (SAZ_SOMA / 12) * ruido(0.05)
                b_cheio = cheio / (bm25 * ruido(0.03))
                f_cheio = b_cheio * pd25 * ruido(0.03)
            else:
                cheio = None
            if cheio is not None:
                frac = 1.0
                if mes == mes_atual:  # mês em andamento: só os dias já fechados
                    frac = dias_loja(2026, mes, loja, ate=ULTIMO_DIA_COM_VENDA) / dias_loja(2026, mes, loja)
                    frac *= ruido(0.06)
                fin26, bol26, fis26 = cheio * frac, b_cheio * frac, f_cheio * frac
        # ---- metas do ano inteiro
        # metas: a rede pede +3% sobre 2025 em todas as lojas; a meta interna do grupo é um pouco mais alta
        if fat25:
            base_meta = fin25 * 1.025
        elif mes >= 2:
            rampa = {2: 0.55, 3: 0.8, 4: 0.92}.get(mes, 1.0)
            base_meta = MAV_MENSAL_MADURO * rampa * SAZONAL[mes - 1] / (SAZ_SOMA / 12)
        else:
            base_meta = None
        meta_int = base_meta * random.uniform(1.00, 1.04) if base_meta else None
        meta_rede = base_meta * random.uniform(0.98, 1.00) if base_meta else None
        # no mês em andamento, a planilha compara com os mesmos dias de 2025 (não com o mês inteiro)
        fin25_mes, bol25_mes, fis25_mes = fin25, bol25, fis25
        if mes == mes_atual and fin25:
            f25 = dias_loja(2026, mes, loja, ate=ULTIMO_DIA_COM_VENDA) / dias_loja(2026, mes, loja)
            fin25_mes, bol25_mes, fis25_mes = fin25 * f25, bol25 * f25, fis25 * f25
        r["_fin25_cheio"] = fin25
        r.update(fis25=arred(fis25_mes, 0), fin25=arred(fin25_mes), bol25=arred(bol25_mes, 0),
                 fis26=arred(fis26, 0), fin26=arred(fin26), bol26=arred(bol26, 0),
                 metaInterna=arred(meta_int), realMeta=arred(fin26), metaRede=arred(meta_rede), realRede=arred(fin26))
        # ---- ritmo diário do mês em andamento (como a planilha calcula)
        r.update(finDiaInterna=None, finDiaRede=None, diasMesPlan=None, diasRestPlan=None, diaMeta=None, diaReal=None)
        if mes == mes_atual and meta_int:
            rest = dias_loja(2026, mes, None, desde=HOJE)   # a planilha usa uma contagem única
            r["diasMesPlan"] = dias_loja(2026, mes, None)
            r["diasRestPlan"] = rest
            r["finDiaInterna"] = arred(-(meta_int - (fin26 or 0)) / rest)
            r["finDiaRede"] = arred(-(meta_rede - (fin26 or 0)) / rest)
        # ---- desafio do dia (definido pela gerente) e venda do dia
        if meta_int and fin26:
            ritmo = meta_int / dias_loja(2026, mes, loja)
            r["diaMeta"] = round(ritmo * random.uniform(1.0, 1.15) / 50) * 50
            parcial = random.uniform(0.35, 0.75) if mes == mes_atual else random.uniform(0.85, 1.18)
            r["diaReal"] = arred(r["diaMeta"] * parcial)
        rows.append(r)

base2025 = {l: [next(round(x["_fin25_cheio"] or 0, 2) for x in rows if x["loja"] == l and x["mes"] == m) for m in range(1, 13)]
            for l in LOJAS}
pesos = {l: v[5] for l, v in LOJAS.items()}
for r in rows:
    del r["_fin25_cheio"]

saida = {
    "aviso": "Dados fictícios gerados por scripts/gerar_dados.py. Não representam nenhuma empresa real.",
    "hoje": HOJE.isoformat(),
    "atualizado": dt.datetime(2026, 11, 18, 14, 30).isoformat(),
    "rows": sorted(rows, key=lambda x: (x["mes"], list(LOJAS).index(x["loja"]))),
    "pesos2027": pesos,
    "base2025": base2025,
}
destino = Path(__file__).resolve().parent.parent / "dados.json"
destino.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

tot25 = sum(sum(v) for v in base2025.values())
tot26 = sum(r["fin26"] or 0 for r in rows)
print(f"{len(rows)} linhas · 2025: R$ {tot25:,.0f} · 2026 até {ULTIMO_DIA_COM_VENDA:%d/%m}: R$ {tot26:,.0f}")
