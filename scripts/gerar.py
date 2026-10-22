"""Valida data/recursos.yaml e gera o catálogo no README.md e em data/recursos.json.

Uso: python3 scripts/gerar.py [--check]
"""

import json
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "data" / "recursos.yaml"
README = RAIZ / "README.md"
JSON = RAIZ / "data" / "recursos.json"
INICIO = "<!-- catalogo:inicio — gerado por scripts/gerar.py a partir de data/recursos.yaml; não edite à mão -->"
FIM = "<!-- catalogo:fim -->"
ORIGENS = {"colmeia", "hub-comite-tecnologia"}
CAMPOS = {"nome", "url", "descricao", "formato", "codigo", "links", "origem"}


def validar(dados):
    erros = []
    ids, urls = set(), set()

    def checar_url(url, onde):
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            erros.append(f"{onde}: url inválida {url!r}")
        elif url in urls:
            erros.append(f"{onde}: url repetida {url}")
        else:
            urls.add(url)

    for cat in dados.get("categorias", []):
        cid = cat.get("id")
        if not cid or not cat.get("titulo"):
            erros.append(f"categoria sem id ou titulo: {cat}")
        if cid in ids:
            erros.append(f"categoria repetida: {cid}")
        ids.add(cid)
        for rec in cat.get("recursos", []):
            onde = f"{cid} › {rec.get('nome', '?')}"
            if not rec.get("nome"):
                erros.append(f"{onde}: falta nome")
            extras = set(rec) - CAMPOS
            if extras:
                erros.append(f"{onde}: campos desconhecidos {sorted(extras)}")
            if rec.get("origem") not in ORIGENS:
                erros.append(f"{onde}: origem deve ser uma de {sorted(ORIGENS)}")
            if ("url" in rec) == ("links" in rec):
                erros.append(f"{onde}: use url ou links, não ambos nem nenhum")
            if "url" in rec:
                checar_url(rec["url"], onde)
            if "codigo" in rec:
                checar_url(rec["codigo"], onde)
            for link in rec.get("links", []):
                if not link.get("nome"):
                    erros.append(f"{onde}: link sem nome")
                checar_url(link.get("url"), onde)
    return erros


def item_markdown(rec):
    if "links" in rec:
        links = [f"[{l['nome']}]({l['url']})" for l in rec["links"]]
        corpo = [f"  {l}," for l in links[:-2]]
        if len(links) > 1:
            corpo.append(f"  {links[-2]} e")
        corpo.append(f"  {links[-1]}.")
        return "\n".join([f"- **{rec['nome']}:**", *corpo])
    linha = f"- **[{rec['nome']}]({rec['url']})**"
    if rec.get("formato"):
        linha += f" ({rec['formato']})"
    if rec.get("codigo"):
        linha += f" ([código]({rec['codigo']}))"
    if rec.get("descricao"):
        linha += f": {rec['descricao']}"
    return linha


def catalogo_markdown(dados):
    secoes = []
    for cat in dados["categorias"]:
        itens = "\n".join(item_markdown(r) for r in cat["recursos"])
        secoes.append(f"## {cat['titulo']}\n\n{itens}")
    return "\n\n".join(secoes)


def catalogo_json(dados):
    recursos = [
        {"categoria": cat["id"], **rec}
        for cat in dados["categorias"]
        for rec in cat["recursos"]
    ]
    saida = {
        "fonte": "https://github.com/colmeiabrasil/diretorio",
        "licenca": "CC0-1.0",
        "total": len(recursos),
        "categorias": [{"id": c["id"], "titulo": c["titulo"]} for c in dados["categorias"]],
        "recursos": recursos,
    }
    return json.dumps(saida, ensure_ascii=False, indent=2) + "\n"


def readme_atualizado(atual, catalogo):
    antes, resto = atual.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    return f"{antes}{INICIO}\n\n{catalogo}\n\n{FIM}{depois}"


def main():
    checar = "--check" in sys.argv[1:]
    dados = yaml.safe_load(FONTE.read_text(encoding="utf-8"))
    erros = validar(dados)
    if erros:
        print("\n".join(erros), file=sys.stderr)
        return 1

    saidas = {
        README: readme_atualizado(README.read_text(encoding="utf-8"), catalogo_markdown(dados)),
        JSON: catalogo_json(dados),
    }
    desatualizados = []
    for caminho, conteudo in saidas.items():
        if caminho.exists() and caminho.read_text(encoding="utf-8") == conteudo:
            continue
        if checar:
            desatualizados.append(caminho.relative_to(RAIZ))
        else:
            caminho.write_text(conteudo, encoding="utf-8")
            print(f"atualizado: {caminho.relative_to(RAIZ)}")
    if desatualizados:
        lista = ", ".join(map(str, desatualizados))
        print(f"desatualizado: {lista}. Rode python3 scripts/gerar.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
