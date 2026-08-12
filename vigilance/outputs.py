"""Write the report to a CSV file and a shareable HTML dashboard."""

import os

RED = "#d64545"
GREEN = "#2e9e5b"


def _ensure_dir(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def write_csv(windows, flagged, path):
    _ensure_dir(path)
    rows = ["reviewer,window,score,flagged"]
    for reviewer in sorted(windows):
        mark = "yes" if reviewer in flagged else "no"
        for index, score in enumerate(windows[reviewer], start=1):
            rows.append(reviewer + "," + str(index) + "," + str(round(score)) + "," + mark)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


def _svg_line(scores, color, width=320, height=90, pad=12):
    points = scores if len(scores) > 1 else (scores + scores if scores else [])
    if not points:
        return ""
    n = len(points)
    coords = []
    for i, value in enumerate(points):
        x = pad + (width - 2 * pad) * (i / (n - 1))
        y = pad + (height - 2 * pad) * (1 - value / 100.0)
        coords.append(str(round(x, 1)) + "," + str(round(y, 1)))
    pts = " ".join(coords)
    return (
        '<svg width="' + str(width) + '" height="' + str(height) + '" '
        'viewBox="0 0 ' + str(width) + ' ' + str(height) + '">'
        '<line x1="' + str(pad) + '" y1="' + str(height - pad) + '" '
        'x2="' + str(width - pad) + '" y2="' + str(height - pad) + '" '
        'stroke="#dfe3e8" stroke-width="1"/>'
        '<polyline fill="none" stroke="' + color + '" stroke-width="3" '
        'points="' + pts + '"/>'
        '</svg>'
    )


CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 24px; background: #f6f7f9; color: #1c2530; }
h1 { margin: 0 0 4px; font-size: 22px; }
.sub { color: #6b7684; margin-bottom: 20px; font-size: 14px; }
.panel { padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-weight: 600; }
.panel.alert { background: #fdecec; color: #b02a2a; border: 1px solid #f3c2c2; }
.panel.clear { background: #eaf6ee; color: #1e7a43; border: 1px solid #bfe4cc; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-bottom: 24px; }
.card { background: #fff; border: 1px solid #e6e9ee; border-radius: 10px; padding: 14px 16px; }
.card .name { font-weight: 600; }
.badge { float: right; font-size: 12px; padding: 2px 8px; border-radius: 20px; }
.badge.flag { background: #fdecec; color: #b02a2a; }
.badge.ok { background: #eaf6ee; color: #1e7a43; }
.meta { color: #6b7684; font-size: 13px; margin: 4px 0 8px; }
table { border-collapse: collapse; width: 100%; background: #fff; border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eef1f4; font-size: 14px; }
th { background: #f0f2f5; }
"""


def write_html(windows, flagged, path, source="simulate"):
    _ensure_dir(path)

    if flagged:
        panel = '<div class="panel alert">Flagged reviewers: ' + ", ".join(sorted(flagged)) + '</div>'
    else:
        panel = '<div class="panel clear">No reviewers flagged.</div>'

    cards = []
    for reviewer in sorted(windows):
        scores = [round(s) for s in windows[reviewer]]
        declining = reviewer in flagged
        color = RED if declining else GREEN
        badge_class = "flag" if declining else "ok"
        badge_text = "FLAGGED" if declining else "ok"
        chart = _svg_line(windows[reviewer], color)
        meta = "first " + str(scores[0]) + " -> latest " + str(scores[-1])
        cards.append(
            '<div class="card">'
            '<span class="badge ' + badge_class + '">' + badge_text + '</span>'
            '<div class="name">' + reviewer + '</div>'
            '<div class="meta">' + meta + '</div>'
            + chart +
            '</div>'
        )

    rows = ['<tr><th>Reviewer</th><th>Window scores</th><th>First</th><th>Latest</th><th>Status</th></tr>']
    for reviewer in sorted(windows):
        scores = [round(s) for s in windows[reviewer]]
        status = "FLAGGED" if reviewer in flagged else "ok"
        rows.append(
            '<tr><td>' + reviewer + '</td><td>' + str(scores) + '</td><td>'
            + str(scores[0]) + '</td><td>' + str(scores[-1]) + '</td><td>'
            + status + '</td></tr>'
        )
    table = '<table>' + "".join(rows) + '</table>'

    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<title>Vigilance dashboard</title><style>' + CSS + '</style></head><body>'
        '<h1>Reviewer Vigilance Dashboard</h1>'
        '<div class="sub">source: ' + source + '</div>'
        + panel +
        '<div class="grid">' + "".join(cards) + '</div>'
        + table +
        '</body></html>'
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(html)
