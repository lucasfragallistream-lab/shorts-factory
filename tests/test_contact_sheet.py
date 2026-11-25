from PIL import Image

from tools import contact_sheet as cs


def test_montar_grade():
    itens = [(Image.new("RGBA", (40, 80), (255, 0, 0, 255)), f"item {i} ação") for i in range(5)]
    folha = cs.montar(itens, colunas=3, thumb=(60, 100), titulo="Título", margem=10, rotulo_px=12)
    assert folha.mode == "RGB"
    assert folha.width == 10 + 3 * 70
    assert folha.height > 2 * 100


def test_cli(tmp_path):
    imgs = []
    for i in range(3):
        p = tmp_path / f"q{i}.png"
        Image.new("RGB", (108, 192), (i * 80, 0, 0)).save(p)
        imgs.append(str(p))
    saida = tmp_path / "cs.png"
    assert cs.main([*imgs, "--saida", str(saida), "--colunas", "2"]) == 0
    assert Image.open(saida).width == 10 + 2 * (216 + 10)
