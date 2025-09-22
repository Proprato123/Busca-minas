#!/usr/bin/env python3
"""
mk_mines_md.py
Genera un tablero estilo "contributions heatmap" convertido a Buscaminas
Uso: python mk_mines_md.py <github_username> [--outfile fichero.md]
Salida: imprime en stdout el markdown listo para pegar en README.md
"""

import sys
import requests
from bs4 import BeautifulSoup
import argparse

def fetch_contributions_svg(username):
    url = f"https://github.com/users/{username}/contributions"
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"No se pudo obtener SVG de contribuciones: status {r.status_code}")
    return r.text

def parse_svg_to_grid(svg_text):
    soup = BeautifulSoup(svg_text, "html.parser")
    rects = soup.find_all("rect", {"data-date": True})
    # agrupamos por x (columnas / semanas) usando el atributo x si está
    cols_by_x = {}
    for rect in rects:
        date = rect.get("data-date")
        count = int(rect.get("data-count", "0"))
        x = rect.get("x")
        y = rect.get("y")
        # si no hay x, fallback a obtener posición por orden (no común)
        key = int(float(x)) if x is not None else None
        entry = {"date": date, "count": count, "x": key, "y": y}
        if key is None:
            # fallback: append to special key
            cols_by_x.setdefault("__no_x__", []).append(entry)
        else:
            cols_by_x.setdefault(key, []).append(entry)
    # si usamos coordenadas x ordenadas, generamos columnas ordenadas
    if "__no_x__" in cols_by_x and len(cols_by_x) == 1:
        # todo en orden; chunk por 7
        all_entries = cols_by_x["__no_x__"]
        weeks = [all_entries[i:i+7] for i in range(0, len(all_entries), 7)]
    else:
        keys = sorted(k for k in cols_by_x.keys() if k != "__no_x__")
        weeks = []
        for k in keys:
            # ordenar por y para que la fila 0 sea la parte superior (Sun..Sat)
            col = sorted(cols_by_x[k], key=lambda e: float(e["y"]) if e["y"] is not None else 0)
            weeks.append(col)
        if "__no_x__" in cols_by_x:
            # append the fallback columns at the end
            more = [cols_by_x["__no_x__"][i:i+7] for i in range(0, len(cols_by_x["__no_x__"]), 7)]
            weeks.extend(more)
    # normalizar: cada columna debe tener 7 filas (si no, rellenar con count=0)
    norm_weeks = []
    for col in weeks:
        if len(col) < 7:
            # llenar hasta 7 con fechas None
            needed = 7 - len(col)
            col = col + [{"date": None, "count": 0}] * needed
        norm_weeks.append(col[:7])
    return norm_weeks

def build_mine_board(weeks):
    cols = len(weeks)
    rows = max(len(col) for col in weeks) if cols>0 else 0
    board = [[{"mine": False, "count": 0, "date": None} for _ in range(rows)] for _ in range(cols)]
    for c in range(cols):
        for r in range(rows):
            entry = weeks[c][r] if r < len(weeks[c]) else {"date": None, "count": 0}
            board[c][r]["count"] = entry.get("count", 0)
            board[c][r]["date"] = entry.get("date", None)
            # regla: si count > 0 => mina (puedes cambiar a >=N)
            board[c][r]["mine"] = entry.get("count", 0) > 0
    # calcular adyacencia (8 vecinos)
    for c in range(cols):
        for r in range(rows):
            adj = 0
            for dc in (-1,0,1):
                for dr in (-1,0,1):
                    if dc==0 and dr==0: continue
                    nc = c+dc; nr = r+dr
                    if 0 <= nc < cols and 0 <= nr < rows:
                        if board[nc][nr]["mine"]:
                            adj += 1
            board[c][r]["adj"] = adj
    return board

def board_to_markdown(board, username, reveal_all=True):
    # símbolos:
    S_EMPTY = "⬛"   # sin dato / sin contribución
    S_SAFE = "⬜"    # casilla revelada sin adyacentes
    S_MINE = "💣"    # mina
    S_CONTR = "🟩"   # contribución (si quieres mostrar no revelada)
    # Armamos las filas para imprimir (GitHub contrib map es por columnas semanales)
    cols = len(board)
    rows = len(board[0]) if cols>0 else 0
    lines = []
    lines.append("```markdown")
    lines.append(f"## 🎮 Buscaminas de Contribuciones — usuario: {username}\n")
    # Queremos mostrar muy ancho (semanas a lo largo). Imprimimos fila por fila (top -> bottom)
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            cell = board[c][r]
            if cell["mine"]:
                # si revelado -> 💣, si no -> 🟩 (pero queremos 'quemado' mostrar minas)
                if reveal_all:
                    symbol = S_MINE
                else:
                    symbol = S_CONTR
            else:
                if reveal_all:
                    if cell["adj"] > 0:
                        symbol = str(cell["adj"])
                    else:
                        symbol = S_SAFE
                else:
                    symbol = S_EMPTY
            row_cells.append(symbol)
        lines.append("".join(row_cells))
    lines.append("\n💥 **¡Boom!** Las casillas marcadas como 💣 representan días con contribuciones (minas).")
    lines.append("🔎 Los números indican cuántas minas hay en las 8 casillas alrededor.")
    lines.append("```")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Genera Markdown tipo Buscaminas desde contribuciones de GitHub")
    parser.add_argument("username", help="GitHub username (ej: EmmanuelPerezVivas)")
    parser.add_argument("--outfile", "-o", help="Archivo de salida (opcional). Si no, imprime por stdout.")
    parser.add_argument("--reveal-all", action="store_true", help="Mostrar todas las minas y números en el tablero (quedado).")
    args = parser.parse_args()

    try:
        svg = fetch_contributions_svg(args.username)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    weeks = parse_svg_to_grid(svg)
    if not weeks:
        print("[ERROR] No se pudo construir la cuadrícula de contribuciones")
        sys.exit(1)

    board = build_mine_board(weeks)
    md = board_to_markdown(board, args.username, reveal_all=args.reveal_all or True)

    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Markdown escrito en {args.outfile}")
    else:
        print(md)

if __name__ == "__main__":
    main()
