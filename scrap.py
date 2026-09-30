import requests
from bs4 import BeautifulSoup
import json

headers = {"User-Agent": "Mozilla/5.0"}

# Cada categoria tem o link da KaBuM e o da Gigantec.
# Para incluir outra, é só acrescentar uma linha aqui.
categorias = {
    "Placa de vídeo": {
        "KaBuM": "https://www.kabum.com.br/hardware/placa-de-video-vga",
        "Gigantec": "https://www.gigantec.com.br/hardware-pecas/placas-de-video.html",
    },
    "Memória RAM": {
        "KaBuM": "https://www.kabum.com.br/hardware/memoria-ram",
        "Gigantec": "https://www.gigantec.com.br/hardware-pecas/memorias.html",
    },
    "Placa-mãe": {
        "KaBuM": "https://www.kabum.com.br/hardware/placas-mae",
        "Gigantec": "https://www.gigantec.com.br/hardware-pecas/placas-m-e.html",
    },
    "Processador": {
        "KaBuM": "https://www.kabum.com.br/hardware/processadores",
        "Gigantec": "https://www.gigantec.com.br/hardware-pecas/processadores.html",
    },
}


def formatar_preco(valor):
    # 1299.99 -> "R$ 1.299,99"
    texto = f"{valor:,.2f}"                # 1,299.99
    texto = texto.replace(",", "X")        # 1X299.99
    texto = texto.replace(".", ",")        # 1X299,99
    texto = texto.replace("X", ".")        # 1.299,99
    return "R$ " + texto


def busca_kabum(url):
    # Devolve uma lista de produtos: [{"nome": ..., "preco": ...}, ...]
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"o site respondeu {r.status_code} (provável bloqueio)")
    soup = BeautifulSoup(r.content, "html.parser")

    # A KaBuM guarda os produtos num JSON dentro da página
    tag = soup.select_one("script#__NEXT_DATA__")
    dados = json.loads(tag.text)
    # o campo "data" é outro JSON escrito como texto, então converte de novo
    catalogo = json.loads(dados["props"]["pageProps"]["data"])

    produtos = []
    for produto in catalogo["catalogServer"]["data"]:
        if not produto["available"]:       # indisponível: ignora
            continue
        # preço à vista (equivale ao "à vista no PIX" da outra loja)
        oferta = produto.get("offer")
        if oferta and oferta.get("priceWithDiscount"):
            preco = oferta["priceWithDiscount"]
        else:
            preco = produto["priceWithDiscount"]
        produtos.append({"nome": produto["name"], "preco": float(preco)})
    return produtos


def busca_gigantec(url):
    # A Gigantec mostra cada produto num "cartão" no HTML
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"o site respondeu {r.status_code} (provável bloqueio)")
    soup = BeautifulSoup(r.content, "html.parser")

    produtos = []
    for cartao in soup.select("li.product-item"):
        nome = cartao.select_one("a.product-item-link")
        preco = cartao.select_one('span[data-price-type="AvistaPrice"]')
        # os 4 primeiros cartões de toda página são propaganda (nome vazio): ignora
        if nome and preco and nome.get_text(strip=True):
            produtos.append({
                "nome": nome.get_text(strip=True),
                "preco": float(preco["data-price-amount"]),   # já vem como número
            })
    return produtos


def filtrar(produtos, termo):
    # Fica só com os produtos que têm o termo no nome (ex: "rtx 4060")
    termo = termo.lower().replace(" ", "")
    achados = []
    for produto in produtos:
        nome = produto["nome"].lower().replace(" ", "")
        if termo in nome:
            achados.append(produto)
    return achados


def menor_preco(produtos):
    menor = produtos[0]
    for produto in produtos:
        if produto["preco"] < menor["preco"]:
            menor = produto
    return menor


def main():
    # 1) escolher a categoria
    nomes = list(categorias)
    for numero, nome in enumerate(nomes, start=1):
        print(f"{numero} - {nome}")
    escolha = int(input("Escolha a categoria (número): "))
    categoria = categorias[nomes[escolha - 1]]

    # 2) escolher o produto a comparar
    termo = input("Qual produto quer comparar? (ex: rtx 4060, ddr5, ryzen 5): ")

    # 3) buscar e filtrar em cada loja
    resultado = {}
    for loja in ["KaBuM", "Gigantec"]:
        try:
            if loja == "KaBuM":
                produtos = busca_kabum(categoria[loja])
            else:
                produtos = busca_gigantec(categoria[loja])
        except Exception as erro:
            print(f"[{loja}] não consegui ler a página: {erro}")
            continue

        achados = filtrar(produtos, termo)
        print(f"[{loja}] {len(produtos)} produtos lidos, {len(achados)} com '{termo}'")
        if achados:
            resultado[loja] = menor_preco(achados)

    # 4) mostrar e comparar
    print()
    for loja in resultado:
        produto = resultado[loja]
        print(f"{loja}: {formatar_preco(produto['preco'])} - {produto['nome']}")

    if len(resultado) == 2:
        preco_k = resultado["KaBuM"]["preco"]
        preco_g = resultado["Gigantec"]["preco"]
        if preco_k < preco_g:
            print(f"\nMais barato: KaBuM ({formatar_preco(preco_g - preco_k)} a menos)")
        elif preco_g < preco_k:
            print(f"\nMais barato: Gigantec ({formatar_preco(preco_k - preco_g)} a menos)")
        else:
            print("\nOs dois têm o mesmo preço.")
    else:
        print("\nNão deu para comparar: alguma loja não tem esse produto ou falhou.")


main()
