#!/usr/bin/env python3
# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Gera a identidade visual do Domínio Linux (família JLW Security) em app/static/marca/.

Símbolo: escudo (segurança) com a árvore do domínio por dentro — o controlador Linux no topo,
ligado às máquinas membros (Windows, Linux, servidores). Paleta da JLW Security: marinho
#061226, ciano #00D4FF, azul #0A6CFF e verde #3DFFA8 (tons mais escuros sobre fundo claro).

Texto vira contorno (fontTools): os SVGs não dependem de fonte no navegador nem de CSP para
fontes. Fontes Orbitron e Rajdhani sob SIL OFL 1.1 (branding/fontes/OFL-*.txt).
PNG (favicon/apple-touch) por rsvg-convert. Uso:  python3 branding/gerar_marca.py
"""
import os
import subprocess

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "fontes")
SAIDA = os.path.join(os.path.dirname(AQUI), "app", "static", "marca")

PALETA = {
    "escuro": dict(c1="#00D4FF", c2="#0A6CFF", c3="#3DFFA8", preenche="#0A1F3D", texto="#FFFFFF", texto2="#7FE9FF", apoio="#8FA6C4"),
    "claro": dict(c1="#0091D5", c2="#0B4FD9", c3="#00A86B", preenche="#EAF4FF", texto="#0A1A33", texto2="#0B4FD9", apoio="#52647B"),
}


def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


class Fonte:
    def __init__(self, arquivo, wght=None):
        f = TTFont(os.path.join(FONTES, arquivo))
        if wght and "fvar" in f:
            f = instantiateVariableFont(f, {"wght": wght})
        self.gs, self.cmap = f.getGlyphSet(), f.getBestCmap()
        bp = BoundsPen(self.gs)
        self.gs[self.cmap[ord("H")]].draw(bp)
        self.cap = bp.bounds[3]

    def largura(self, s, cap, track=0.0):
        k = cap / self.cap
        return sum(self.gs[self.cmap.get(ord(c), ".notdef")].width * k for c in s) + track * cap * (len(s) - 1)

    def path(self, s, x, y, cap, track=0.0):
        k, pen, cx = cap / self.cap, SVGPathPen(self.gs, ntos=n), 0.0
        for c in s:
            g = self.cmap.get(ord(c), ".notdef")
            self.gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x + cx, y)))
            cx += self.gs[g].width * k + track * cap
        return pen.getCommands()


ORB_FORTE = Fonte("Orbitron[wght].ttf", wght=900)
ORB_LEVE = Fonte("Orbitron[wght].ttf", wght=500)
RAJ = Fonte("Rajdhani-Bold.ttf")

ESCUDO = "M32 4 L54 12 V30 C54 44.5 44.5 53.5 32 60 C19.5 53.5 10 44.5 10 30 V12 Z"


def simbolo(tom, uid, reduzido=False):
    """Escudo 64×64 com a árvore do domínio. `reduzido` = traços grossos para 16–32 px."""
    p = PALETA[tom]
    g = f"g{uid}"
    defs = (f'<linearGradient id="{g}" x1="10" y1="4" x2="54" y2="60" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{p["c1"]}"/><stop offset="1" stop-color="{p["c2"]}"/></linearGradient>')
    if reduzido:
        corpo = (f'<path d="{ESCUDO}" fill="{p["preenche"]}" stroke="url(#{g})" stroke-width="5" stroke-linejoin="round"/>'
                 f'<path d="M32 23 L21 41 M32 23 L43 41" stroke="{p["c1"]}" stroke-width="3.6" stroke-linecap="round" fill="none"/>'
                 f'<circle cx="32" cy="22" r="6.5" fill="{p["c1"]}"/>'
                 f'<circle cx="21" cy="42" r="5" fill="{p["c2"]}"/><circle cx="43" cy="42" r="5" fill="{p["c3"]}"/>')
    else:
        corpo = (f'<path d="{ESCUDO}" fill="{p["preenche"]}" stroke="url(#{g})" stroke-width="3.2" stroke-linejoin="round"/>'
                 # ligações do controlador às máquinas membros
                 f'<path d="M32 26.5 L20.5 39.5 M32 26.5 V43 M32 26.5 L43.5 39.5" stroke="{p["c1"]}" stroke-opacity=".75" '
                 f'stroke-width="2" stroke-linecap="round" fill="none"/>'
                 f'<path d="M20.5 41.5 Q32 49 43.5 41.5" stroke="{p["c2"]}" stroke-opacity=".45" stroke-width="1.4" fill="none"/>'
                 # controlador Linux (anel = serviço ativo)
                 f'<circle cx="32" cy="21.5" r="7.2" fill="none" stroke="{p["c1"]}" stroke-opacity=".45" stroke-width="1.4"/>'
                 f'<circle cx="32" cy="21.5" r="4.6" fill="{p["c1"]}"/>'
                 # membros: Windows, Linux, servidor
                 f'<circle cx="20.5" cy="40.5" r="3.4" fill="{p["c2"]}"/>'
                 f'<circle cx="32" cy="44.5" r="3.4" fill="{p["c1"]}"/>'
                 f'<circle cx="43.5" cy="40.5" r="3.4" fill="{p["c3"]}"/>')
    return defs, corpo


def palavras(tom, x, y):
    """DOMÍNIO LINUX / POR JLW SECURITY. Devolve (corpo, largura, altura)."""
    p = PALETA[tom]
    cap = 17
    w1 = ORB_FORTE.largura("DOMÍNIO", cap, 0.08)
    gap = cap * 0.55
    w2 = ORB_LEVE.largura("LINUX", cap, 0.08)
    cap_s = 7.4
    sub = "POR JLW SECURITY"
    w_tot = w1 + gap + w2
    track = 0.34  # espaçamento fixo: esticar até a largura do nome deixava as letras soltas demais
    corpo = (f'<path fill="{p["texto"]}" d="{ORB_FORTE.path("DOMÍNIO", x, y, cap, 0.08)}"/>'
             f'<path fill="{p["texto2"]}" d="{ORB_LEVE.path("LINUX", x + w1 + gap, y, cap, 0.08)}"/>'
             f'<path fill="{p["apoio"]}" d="{RAJ.path(sub, x, y + 15, cap_s, track)}"/>')
    return corpo, w_tot, cap + 15


def svg(w, h, defs, corpo, titulo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(w)} {n(h)}" width="{n(w)}" height="{n(h)}" role="img">'
            f'<title>{titulo}</title><defs>{defs}</defs>{corpo}</svg>\n')


def grava(nome, conteudo):
    with open(os.path.join(SAIDA, nome), "w") as f:
        f.write(conteudo)


def main():
    os.makedirs(SAIDA, exist_ok=True)
    for tom in ("escuro", "claro"):
        d, c = simbolo(tom, tom)
        grava(f"simbolo-{tom}.svg", svg(64, 64, d, c, "Domínio Linux — JLW Security"))
        # horizontal: símbolo 44 px + texto
        d, c = simbolo(tom, "h" + tom)
        texto, w, _ = palavras(tom, 56, 25)
        grava(f"logo-horizontal-{tom}.svg", svg(56 + w + 2, 44, d,
              f'<g transform="scale(.6875)">{c}</g>{texto}', "Domínio Linux — JLW Security"))
    # ícone do navegador / app: símbolo reduzido sobre quadrado marinho
    d, c = simbolo("escuro", "fav", reduzido=True)
    icone = svg(64, 64, d, f'<rect width="64" height="64" rx="14" fill="#061226"/><g transform="translate(5 4.5) scale(.84)">{c}</g>',
                "Domínio Linux")
    grava("favicon.svg", icone)
    for lado, nome in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (512, "icone-512.png")):
        subprocess.run(["rsvg-convert", "-w", str(lado), "-h", str(lado), "-o", os.path.join(SAIDA, nome),
                        os.path.join(SAIDA, "favicon.svg")], check=True)
    # fundo do painel de entrada: malha de nós e ligações (rede do domínio), bem discreta
    import random
    rnd = random.Random(11)
    W, H = 640, 760
    pts = [(rnd.uniform(0, W), rnd.uniform(0, H)) for _ in range(46)]
    linhas = []
    for i, (x1, y1) in enumerate(pts):
        viz = sorted(pts, key=lambda q: (q[0] - x1) ** 2 + (q[1] - y1) ** 2)[1:3]
        for (x2, y2) in viz:
            linhas.append(f'M{n(x1)} {n(y1)} L{n(x2)} {n(y2)}')
    nos = "".join(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(rnd.choice((1.6, 2.2, 3)))}"/>' for x, y in pts)
    d, c = simbolo("escuro", "fundo")
    fundo = svg(W, H, d + '<radialGradient id="brilho" cx=".78" cy=".22" r=".7"><stop offset="0" stop-color="#0A6CFF" stop-opacity=".35"/>'
                '<stop offset="1" stop-color="#061226" stop-opacity="0"/></radialGradient>',
                f'<rect width="{W}" height="{H}" fill="#061226"/><rect width="{W}" height="{H}" fill="url(#brilho)"/>'
                f'<path d="{" ".join(linhas)}" stroke="#00D4FF" stroke-opacity=".10" stroke-width="1" fill="none"/>'
                f'<g fill="#00D4FF" fill-opacity=".22">{nos}</g>'
                f'<g opacity=".10" transform="translate(330 300) scale(6.2)">{c}</g>', "")
    grava("fundo-entrada.svg", fundo)
    print("gerado em", SAIDA, sorted(os.listdir(SAIDA)))


if __name__ == "__main__":
    main()
