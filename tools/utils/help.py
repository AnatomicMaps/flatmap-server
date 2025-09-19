HELP_HTML_FORMAT = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{stylesheet}
body {{
    color: {foreground};
    background-color: {background};
    padding-left: 10px;
}}
.r7 {{
    background-color: #ccc;
}}
</style>
</head>
<body>
    <pre style="font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">
<code style="font-family:inherit">{code}</code>
    </pre>
</body>
</html>
"""
