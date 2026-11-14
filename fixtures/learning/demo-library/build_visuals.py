import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def node(i, value="", label="", x=0.5, y=0.5, glyph="circle", to=None):
    d = {
        "id": str(i),
        "label": label,
        "value": str(value),
        "x": x,
        "y": y,
        "glyph": glyph,
    }
    if to:
        d.update(to_x=to[0], to_y=to[1])
    return d


def scene(nodes, edges=(), eq="", kind="nodes"):
    return {
        "kind": kind,
        "nodes": nodes,
        "edges": [{"source": str(a), "target": str(b)} for a, b in edges],
        "equation": eq,
    }


def tree(vals, positions=None, target=None, eq=""):
    pos = positions or [
        (0.5, 0.15),
        (0.28, 0.39),
        (0.72, 0.39),
        (0.15, 0.68),
        (0.4, 0.68),
        (0.62, 0.68),
        (0.85, 0.68),
    ]
    return scene(
        [
            node(
                "n" + str(i),
                v,
                x=pos[i][0],
                y=pos[i][1],
                to=(target[i] if target else None),
            )
            for i, v in enumerate(vals)
        ],
        [("n" + str((i - 1) // 2), "n" + str(i)) for i in range(1, len(vals))],
        eq,
        "tree",
    )


def row(values, labels=None, eq="", kind="nodes"):
    return scene(
        [
            node(
                "n" + str(i),
                v,
                (labels or [""] * len(values))[i],
                0.15 + i * 0.7 / max(1, len(values) - 1),
                0.48,
                "box",
            )
            for i, v in enumerate(values)
        ],
        eq=eq,
        kind=kind,
    )


def matrix(values, eq="", labels=None):
    return scene(
        [
            node(
                "m" + str(i) + str(j),
                v,
                (labels or {}).get((i, j), ""),
                0.24 + j * 0.24,
                0.25 + i * 0.27,
                "box",
            )
            for i, r in enumerate(values)
            for j, v in enumerate(r)
        ],
        eq=eq,
        kind="matrix",
    )


def trade(a, b, thing="crate", value="", labels=("", ""), reverse=False):
    src, dst = (0.27, 0.73) if not reverse else (0.73, 0.27)
    return scene(
        [
            node("seller", "", a, 0.15, 0.5, "person"),
            node("buyer", "", b, 0.85, 0.5, "person"),
            node("cargo", value, labels[0], src, 0.4, thing, to=(dst, 0.4)),
        ],
        eq=labels[1],
        kind="inventory",
    )


def visual(key, text, i, n):
    t = text.lower()
    p = i / max(1, n - 1)
    if key == "avl_rotation":
        before = [(0.67, 0.15), (0.46, 0.4), (0.25, 0.67)]
        after = [(0.76, 0.55), (0.5, 0.22), (0.24, 0.55)]
        rot = (
            any(
                w in t
                for w in [
                    "right rotation",
                    "rotate right",
                    "twenty becomes",
                    "20 becomes",
                    "in-order",
                    "inorder",
                ]
            )
            or p > 0.6
        )
        # IDs are values; edges explicitly change after rotation to preserve BST.
        nodes = [
            node(
                str(v), v, x=before[j][0], y=before[j][1], to=after[j] if rot else None
            )
            for j, v in enumerate([30, 20, 10])
        ]
        return scene(
            nodes,
            [(20, 10), (20, 30)] if rot else [(30, 20), (20, 10)],
            "10 < 20 < 30" if rot else "balance = left height − right height",
            "tree",
        )
    if key == "avl_double":
        stage = 2 if i >= 5 else 1 if i == 4 else 0
        positions = [
            [(0.7, 0.16), (0.3, 0.45), (0.5, 0.73)],
            [(0.7, 0.16), (0.3, 0.73), (0.5, 0.45)],
            [(0.78, 0.57), (0.22, 0.57), (0.5, 0.2)],
        ][stage]
        edges = [[(30, 10), (10, 20)], [(30, 20), (20, 10)], [(20, 10), (20, 30)]][
            stage
        ]
        return scene(
            [
                node(v, v, x=positions[j][0], y=positions[j][1])
                for j, v in enumerate([30, 10, 20])
            ],
            edges,
            ["30, 10, 20", "rotate left at 10", "rotate right at 30"][stage],
            "tree",
        )
    if key == "heap_insert":
        vals = (
            [2, 5, 4, 9]
            if p < 0.25
            else [2, 5, 4, 9, 1]
            if p < 0.5
            else [2, 1, 4, 9, 5]
            if p < 0.7
            else [1, 2, 4, 9, 5]
        )
        return tree(vals, eq="parent ≤ children" if p < 0.7 else "[1, 2, 4, 9, 5]")
    if key == "heap_extract":
        vals = (
            [1, 2, 4, 9, 5] if p < 0.28 else [5, 2, 4, 9] if p < 0.65 else [2, 5, 4, 9]
        )
        return tree(
            vals,
            eq="remove 1; move last to root"
            if 0.28 <= p < 0.65
            else "swap with the smaller child"
            if p >= 0.65
            else "minimum is at the root",
        )
    if key == "heap_build":
        return tree(
            [7, 5, 6, 1, 2, 3, 4] if p < 0.45 else [1, 2, 3, 5, 7, 6, 4],
            eq="most nodes are near the leaves"
            if p < 0.5
            else "n/4 + 2n/8 + 3n/16 + … = O(n)",
        )
    if key == "heap_bst":
        return tree(
            [1, 5, 2],
            eq="min-heap: only parent ≤ children"
            if p < 0.5
            else "not BST order: left subtree may be larger",
        )
    if key == "cogs":
        return row(
            ["1,000", "4,000", "1,200"] if p < 0.65 else ["5,000", "1,200", "3,800"],
            ["Beginning", "Net purchases", "Ending"]
            if p < 0.65
            else ["Available", "Ending", "COGS"],
            eq="1,000 + 4,000 − 1,200 = 3,800",
        )
    if key == "perpetual":
        if i < 3:
            return trade(
                "Store", "Customer", "crate", "$60", ("Cost", "$100 cash sale")
            )
        if i == 3:
            return row(
                ["+100", "+100"],
                ["Cash (debit)", "Sales (credit)"],
                eq="record revenue: $100",
            )
        return row(
            ["+60", "−60"],
            ["COGS (debit)", "Inventory (credit)"],
            eq="record cost: $60; gross profit: $40",
        )
    if key == "fifo":
        nodes = [
            node(
                "c" + str(j),
                "$10" if j < 2 else "$12",
                "",
                0.14 + j * 0.18,
                0.4,
                "crate",
                to=(0.14 + j * 0.18, 0.72) if j < 3 and p > 0.4 else None,
            )
            for j in range(5)
        ]
        return scene(
            nodes,
            eq="COGS: 10 + 10 + 12 = 32"
            if p > 0.4
            else "2 units at $10, then 3 at $12",
            kind="inventory",
        )
    if key == "returns":
        return (
            trade(
                "Store",
                "Customer",
                "crate",
                "$60",
                ("Resalable", "restore inventory at original cost"),
                True,
            )
            if p < 0.7
            else row(
                ["+60", "−60"],
                ["Inventory", "COGS"],
                eq="return reverses cost recognition",
            )
        )
    if key == "balance_sheet":
        if i < 4:
            return row(
                ["300", "700", "1,000"],
                ["Current assets", "Equipment", "Total assets"],
                eq="at a specific date",
            )
        return row(
            ["1,000", "500", "500"],
            ["Assets", "Liabilities", "Equity"],
            eq="Liabilities: 200 current + 300 long-term",
        )
    if key == "accounting_equation":
        if i < 2:
            return row(
                ["1,000", "400", "600"],
                ["Assets", "Liabilities", "Equity"],
                eq="A = L + E",
            )
        if i < 4:
            return row(
                ["1,500", "900", "600"],
                ["Assets", "Liabilities", "Equity"],
                eq="borrow $500: cash and debt rise",
            )
        if i == 4:
            return row(
                ["1,700", "900", "800"],
                ["Assets", "Liabilities", "Equity"],
                eq="owner invests $200: cash and equity rise",
            )
        return row(
            ["−300", "+300", "0"],
            ["Cash", "Inventory", "Change in assets"],
            eq="buy inventory: total assets stay $1,700",
        )
    if key == "monsoon_trade":
        return trade(
            "East Africa",
            "India",
            "crate",
            "",
            ("Cargo", "seasonal winds reverse"),
            i == 3 or i >= 6,
        )
    if key == "mali":
        return scene(
            [
                node(
                    "gold",
                    "",
                    "Gold",
                    0.2,
                    0.55,
                    "coin",
                    to=(0.58, 0.55) if p > 0.3 else None,
                ),
                node(
                    "salt",
                    "",
                    "Salt",
                    0.8,
                    0.3,
                    "crate",
                    to=(0.42, 0.3) if p > 0.3 else None,
                ),
                node("city", "", "Mali trade", 0.5, 0.75, "person"),
            ],
            eq="Mansa Musa’s pilgrimage: 1324"
            if p > 0.65
            else "trade + taxation supported state wealth",
        )
    if key == "mongols":
        nodes = [
            node("a", "", "East Asia", 0.15, 0.4, "box"),
            node("b", "", "Central Asia", 0.5, 0.4, "box"),
            node("c", "", "West Asia", 0.85, 0.4, "box"),
            node("r", "", "Courier", 0.17, 0.72, "person", to=(0.8, 0.72)),
        ]
        return scene(
            nodes, [("a", "b"), ("b", "c")], eq="conquest + administration + exchange"
        )
    if key == "plague_labor":
        if i < 3:
            return scene(
                [
                    node("w" + str(j), "", "Worker", 0.13 + j * 0.19, 0.5, "person")
                    for j in range(4)
                ]
                + [node("land", "", "Landowner", 0.89, 0.5, "person")],
                eq="labor before the shock",
            )
        people = [
            node("w1", "", "Worker", 0.25, 0.5, "person"),
            node("w2", "", "Worker", 0.5, 0.5, "person"),
            node("land", "", "Landowner", 0.8, 0.5, "person"),
        ]
        if i >= 4:
            people.append(
                node("pay", "", "Wage offer", 0.72, 0.22, "coin", to=(0.36, 0.22))
            )
        return scene(people, eq="fewer workers → bargaining pressure")
    if key == "printing":
        return scene(
            [
                node("wood", "868", "China: woodblocks", 0.13, 0.55, "book"),
                node("type", "1040s", "Bi Sheng", 0.38, 0.4, "box"),
                node("korea", "1377", "Korea: metal type", 0.63, 0.55, "book"),
                node("europe", "1450s", "Gutenberg", 0.88, 0.4, "book"),
            ],
            eq="printing developed across regions",
            kind="timeline",
        )
    if key == "byzantium":
        return scene(
            [
                node("west", "476", "Western emperor", 0.18, 0.5, "box"),
                node("east", "1453", "Constantinople", 0.8, 0.5, "box"),
                node("law", "500s", "Justinian’s law", 0.5, 0.3, "book"),
            ],
            [("west", "east")],
            eq="the eastern empire continued after 476",
            kind="timeline",
        )
    if key == "matrix_multiplication":
        if i == 2:
            return row(["1×2", "2×1", "4"], ["", "", "entry (1,1)"], eq="1×2 + 2×1 = 4")
        if i == 3:
            return row(["1×0", "2×2", "4"], ["", "", "entry (1,2)"], eq="1×0 + 2×2 = 4")
        if i == 4:
            return row(
                ["10", "8"], ["entry (2,1)", "entry (2,2)"], eq="3×2+4×1=10; 3×0+4×2=8"
            )
        a, b = [[1, 2], [3, 4]], [[2, 0], [1, 2]]
        if i == 6:
            a, b = b, a
        return {
            "kind": "matrix",
            "nodes": [],
            "edges": [],
            "equation": "",
            "matrix_a": a,
            "matrix_b": b,
        }
    if key == "rank":
        return matrix(
            [[1, 2], [2, 4]] if p < 0.6 else [[1, 2], [0, 0]],
            eq="R₂ = 2R₁ → rank = 1"
            if p < 0.6
            else "one pivot; one independent direction",
        )
    if key == "rref":
        if i == 6:
            return matrix([[1, 2, 5], [0, 0, 1]], eq="0 = 1 → no solution")
        return matrix(
            [[1, 2, 5], [2, 4, 10]] if i < 2 else [[1, 2, 5], [0, 0, 0]],
            eq="R₂ ← R₂ − 2R₁" if i < 4 else "y = t; x = 5 − 2t",
        )
    if key == "determinant":
        if i == 6:
            return scene(
                [
                    node("a", "", "", 0.2, 0.65),
                    node("b", "", "", 0.4, 0.65, to=(0.7, 0.65)),
                    node("c", "", "", 0.4, 0.45, to=(0.7, 0.65)),
                    node("d", "", "", 0.2, 0.45, to=(0.2, 0.65)),
                ],
                [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")],
                eq="det = 0: area collapses",
            )
        return scene(
            [
                node("p0", "", "", 0.2, 0.65, "circle"),
                node("p1", "", "", 0.4, 0.65, "circle", to=(0.6, 0.65)),
                node("p2", "", "", 0.4, 0.45, "circle", to=(0.8, 0.05)),
                node("p3", "", "", 0.2, 0.45, "circle", to=(0.4, 0.05)),
            ],
            [("p0", "p1"), ("p1", "p2"), ("p2", "p3"), ("p3", "p0")],
            eq="det [[2,1],[0,3]] = 6; area × 6",
        )
    if key == "nullspace":
        return scene(
            [
                node("actor", "", "", 0.1, 0.65, "person"),
                node("v", "(−2,1)", "input", 0.28, 0.4, "box", to=(0.32, 0.4)),
                node("a", "", "A", 0.5, 0.4, "box"),
                node("zero", "(0, 0)", "output", 0.8, 0.4, "box"),
            ],
            [("v", "a"), ("a", "zero")],
            eq="A = [[1,2],[2,4]]; Ax = 0",
        )
    if key == "eigenvectors":
        return scene(
            [
                node("origin", "", "", 0.2, 0.7),
                node("e1", "e₁", "λ = 2", 0.4, 0.7, to=(0.6, 0.7)),
                node("e2", "e₂", "λ = 3", 0.2, 0.5, to=(0.2, 0.1)),
            ],
            [("origin", "e1"), ("origin", "e2")],
            eq="A = diag(2, 3); Av = λv",
        )
    raise ValueError(key)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rebuild trusted scene data from reviewed generic scripts"
    )
    parser.add_argument("--input", type=Path, default=HERE / "lessons.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    for lesson in data["lessons"]:
        prefix = lesson["course_id"] + "_"
        if not lesson["lesson_id"].startswith(prefix):
            raise ValueError("Lesson ID must match its generic demo course")
        key = lesson["lesson_id"][len(prefix) :]
        lesson["visual_plan"] = [
            visual(key, segment["spoken_text"], index, len(lesson["segments"]))
            for index, segment in enumerate(lesson["segments"])
        ]
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        str(len(data["lessons"]))
        + " generic scene plans rebuilt; factual/render review still required"
    )
